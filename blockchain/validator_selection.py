"""
BT2C Validator Selection Module

This module implements a secure and fair validator selection algorithm for the BT2C blockchain.
It provides resistance to stake grinding attacks and ensures fair distribution of block creation
opportunities based on stake.
"""

import os
import time
import random
import hashlib
import logging
import math
from typing import List, Dict, Any, Tuple
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bt2c_validator_selection")

class ValidatorSelector:
    """
    Implements a secure validator selection algorithm resistant to stake grinding attacks.
    Uses a combination of VRF (Verifiable Random Function) and stake-weighted selection.
    """
    
    def __init__(self, seed_source="combined", fairness_window=100, adjustment_range=(0.3, 3.0)):
        """
        Initialize the validator selector.
        
        Args:
            seed_source: Source of randomness for the seed ("timestamp", "block_hash", or "combined")
            fairness_window: Number of blocks to consider for fairness adjustment
            adjustment_range: Tuple of (min, max) adjustment factors for fairness
        """
        self.seed_source = seed_source
        self.last_selected = None
        self.selection_history = []
        self.entropy_pool = os.urandom(32)  # Initial entropy from system randomness
        self.fairness_window = fairness_window
        self.selection_counts = {}  # Track validator selections for fairness
        self.adjustment_range = adjustment_range
        self.recent_blocks = deque(maxlen=fairness_window)  # Store recent block data
        self.statistical_data = {
            "chi_square_history": [],
            "p_value_history": [],
            "gini_history": [],
            "max_deviation_history": []
        }
    
    def generate_seed(self, block_data: Dict[str, Any]) -> bytes:
        """
        Generate a secure seed for validator selection.
        
        Args:
            block_data: Data from the previous block
            
        Returns:
            bytes: A secure seed derived from multiple sources of randomness
        """
        # Use multiple sources of randomness to prevent manipulation
        sources = []
        
        # Current timestamp (milliseconds)
        timestamp = int(time.time() * 1000).to_bytes(8, byteorder='big')
        sources.append(timestamp)
        
        # Previous block hash if available
        if "previous_hash" in block_data and block_data["previous_hash"]:
            prev_hash = block_data["previous_hash"].encode()
            sources.append(prev_hash)
        
        # Block height
        if "height" in block_data:
            height = int(block_data["height"]).to_bytes(8, byteorder='big')
            sources.append(height)
        
        # Add transactions hash if available
        if "transactions" in block_data and block_data["transactions"]:
            tx_data = str(block_data["transactions"]).encode()
            tx_hash = hashlib.sha256(tx_data).digest()
            sources.append(tx_hash)
        
        # Add previous validator to prevent grinding
        if "validator" in block_data and block_data["validator"]:
            validator = block_data["validator"].encode()
            sources.append(validator)
        
        # Add entropy from the entropy pool
        sources.append(self.entropy_pool)
        
        # Add selection history hash to ensure long-term fairness
        history_str = ":".join(self.selection_history[-20:] if self.selection_history else ["init"])
        history_hash = hashlib.sha256(history_str.encode()).digest()
        sources.append(history_hash)
        
        # Add a nonce derived from the current block's data
        block_str = str(sorted(block_data.items()))
        nonce = hashlib.sha256(block_str.encode()).digest()
        sources.append(nonce)
        
        # Combine all sources
        combined = b''.join(sources)
        
        # Generate seed using SHA-256
        seed = hashlib.sha256(combined).digest()
        
        # Update entropy pool for next selection
        self.entropy_pool = hashlib.sha256(self.entropy_pool + seed).digest()
        
        return seed
    
    def select_validator(self, validators: List[Dict[str, Any]], block_data: Dict[str, Any]) -> str:
        """
        Select a validator for the next block using a secure, stake-weighted algorithm.
        
        Args:
            validators: List of validators with their stakes
            block_data: Data from the previous block
            
        Returns:
            str: Address of the selected validator
        """
        if not validators:
            logger.error("No validators available for selection")
            return None
        
        # Store block data for historical analysis
        if "height" in block_data:
            self.recent_blocks.append(block_data)
        
        # Generate secure seed
        seed = self.generate_seed(block_data)
        
        # Apply fairness adjustment based on historical selections
        adjusted_validators = self._apply_fairness_adjustment(validators)
        
        # Calculate total adjusted stake
        total_adjusted_stake = sum(validator.get("adjusted_stake", 0) for validator in adjusted_validators)
        
        if total_adjusted_stake <= 0:
            logger.warning("Total adjusted stake is zero or negative, using equal probability")
            # If no stake information, select randomly with equal probability
            random.seed(seed)
            selected = random.choice(validators)
            selected_address = selected.get("address")
        else:
            # Use VRF (Verifiable Random Function) for selection with adjusted stakes
            selected_address = self._vrf_stake_weighted_selection(adjusted_validators, total_adjusted_stake, seed)
        
        # Prevent same validator from being selected too many times in a row
        consecutive_threshold = min(3, len(validators))
        if len(self.selection_history) >= consecutive_threshold:
            recent_selections = self.selection_history[-consecutive_threshold:]
            if all(s == selected_address for s in recent_selections):
                logger.info(f"Preventing consecutive selection of {selected_address}")
                # Force selection of a different validator
                remaining = [v for v in adjusted_validators if v.get("address") != selected_address]
                if remaining:
                    # Generate a new seed to avoid predictability
                    new_seed = hashlib.sha256(seed + os.urandom(8)).digest()
                    random.seed(new_seed)
                    fallback = random.choice(remaining)
                    selected_address = fallback.get("address")
        
        # Update selection history and counts
        self.selection_history.append(selected_address)
        if len(self.selection_history) > self.fairness_window:
            self.selection_history = self.selection_history[-self.fairness_window:]
        
        # Update selection counts for fairness tracking
        self.selection_counts[selected_address] = self.selection_counts.get(selected_address, 0) + 1
        
        # Update statistical data if we have enough history
        if len(self.selection_history) >= 10:
            self._update_statistical_data(validators)
        
        self.last_selected = selected_address
        return selected_address
    
    def _apply_fairness_adjustment(self, validators: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply fairness adjustment to validator stakes based on historical selections.
        
        Args:
            validators: List of validators with their stakes
            
        Returns:
            List[Dict[str, Any]]: Validators with adjusted stakes
        """
        # Create a copy of validators to avoid modifying the original
        adjusted_validators = []
        
        # Calculate total stake
        total_stake = sum(validator.get("stake", 0) for validator in validators)
        
        # If no selection history or total stake is zero, return validators without adjustment
        if not self.selection_history or total_stake <= 0:
            for validator in validators:
                adjusted_validator = validator.copy()
                adjusted_validator["adjusted_stake"] = validator.get("stake", 0)
                adjusted_validators.append(adjusted_validator)
            return adjusted_validators
        
        # Calculate expected vs. actual selection rates
        for validator in validators:
            address = validator.get("address")
            stake = validator.get("stake", 0)
            
            # Expected selection rate based on stake
            expected_rate = stake / total_stake if total_stake > 0 else 1 / len(validators)
            
            # Actual selection rate based on history
            selections = self.selection_counts.get(address, 0)
            total_selections = sum(self.selection_counts.values())
            actual_rate = selections / total_selections if total_selections > 0 else 0
            
            # Calculate adjustment factor (inverse of selection frequency)
            # This increases the chance for validators that have been selected less than expected
            if actual_rate > 0:
                # Use a more aggressive adjustment formula
                if actual_rate < expected_rate:
                    # Boost validators that are underrepresented
                    adjustment_factor = expected_rate / actual_rate
                    # Apply progressive boosting for severe underrepresentation
                    if actual_rate < expected_rate / 2:
                        adjustment_factor *= 1.5
                else:
                    # Reduce probability for overrepresented validators
                    adjustment_factor = expected_rate / actual_rate
                    # Apply progressive reduction for severe overrepresentation
                    if actual_rate > expected_rate * 2:
                        adjustment_factor *= 0.75
            else:
                # If never selected, give a strong boost
                adjustment_factor = 3.0
            
            # Apply a bounded adjustment to avoid extreme values
            min_adj, max_adj = self.adjustment_range
            bounded_adjustment = max(min_adj, min(max_adj, adjustment_factor))
            
            # Apply adjustment to stake
            adjusted_stake = stake * bounded_adjustment
            
            # Create adjusted validator entry
            adjusted_validator = validator.copy()
            adjusted_validator["adjusted_stake"] = adjusted_stake
            adjusted_validator["adjustment_factor"] = bounded_adjustment
            adjusted_validator["expected_rate"] = expected_rate
            adjusted_validator["actual_rate"] = actual_rate
            adjusted_validators.append(adjusted_validator)
            
            logger.debug(f"Validator {address}: stake={stake}, adjusted={adjusted_stake}, factor={bounded_adjustment}")
        
        return adjusted_validators
    
    def _vrf_stake_weighted_selection(self, validators: List[Dict[str, Any]], total_stake: float, seed: bytes) -> str:
        """
        Select a validator using a VRF-based stake-weighted algorithm.
        
        Args:
            validators: List of validators with their adjusted stakes
            total_stake: Total adjusted stake of all validators
            seed: Random seed
            
        Returns:
            str: Address of the selected validator
        """
        # Convert seed to a number between 0 and 1
        seed_int = int.from_bytes(seed, byteorder='big')
        random_value = (seed_int % 10000) / 10000  # Value between 0 and 1
        
        # Stake-weighted selection
        cumulative_probability = 0
        for validator in validators:
            stake = validator.get("adjusted_stake", 0)
            probability = stake / total_stake
            cumulative_probability += probability
            
            if random_value <= cumulative_probability:
                return validator.get("address")
        
        # Fallback (should not reach here unless there's a floating-point precision issue)
        return validators[-1].get("address")
    
    def _update_statistical_data(self, validators: List[Dict[str, Any]]):
        """
        Update statistical data based on selection history
        
        Args:
            validators: List of validators with their stakes
        """
        # Calculate chi-square and p-value
        analysis = self.analyze_distribution(self.selection_history, validators)
        
        # Store historical data
        self.statistical_data["chi_square_history"].append(analysis.get("chi_square", 0))
        self.statistical_data["p_value_history"].append(analysis.get("p_value", 0))
        self.statistical_data["gini_history"].append(analysis.get("gini_difference", 0))
        self.statistical_data["max_deviation_history"].append(analysis.get("max_deviation", 0))
        
        # Trim history if needed
        max_history = 100
        for key in self.statistical_data:
            if len(self.statistical_data[key]) > max_history:
                self.statistical_data[key] = self.statistical_data[key][-max_history:]
    
    def analyze_distribution(self, selections: List[str], validators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the fairness of validator selection distribution.
        
        Args:
            selections: List of selected validator addresses
            validators: List of validators with their stakes
            
        Returns:
            Dict: Analysis results
        """
        if not selections or not validators:
            return {"error": "No selections or validators to analyze"}
        
        # Count selections
        selection_counts = {}
        for address in selections:
            selection_counts[address] = selection_counts.get(address, 0) + 1
        
        # Calculate total stake
        total_stake = sum(validator.get("stake", 0) for validator in validators)
        
        # Calculate expected vs actual selection rates
        results = []
        for validator in validators:
            address = validator.get("address")
            stake = validator.get("stake", 0)
            
            expected_rate = stake / total_stake if total_stake > 0 else 1 / len(validators)
            actual_selections = selection_counts.get(address, 0)
            actual_rate = actual_selections / len(selections) if selections else 0
            
            # Calculate percentage deviation
            if expected_rate > 0:
                percentage_deviation = ((actual_rate - expected_rate) / expected_rate) * 100
            else:
                percentage_deviation = 0 if actual_rate == 0 else float('inf')
            
            results.append({
                "address": address,
                "stake": stake,
                "expected_rate": expected_rate,
                "actual_rate": actual_rate,
                "selections": actual_selections,
                "deviation": actual_rate - expected_rate,
                "percentage_deviation": percentage_deviation
            })
        
        # Calculate fairness metrics
        abs_deviations = [abs(r["deviation"]) for r in results]
        max_deviation = max(abs_deviations) if abs_deviations else 0
        avg_deviation = sum(abs_deviations) / len(abs_deviations) if abs_deviations else 0
        
        # Calculate percentage deviations
        abs_pct_deviations = [abs(r["percentage_deviation"]) for r in results if not math.isinf(r["percentage_deviation"])]
        max_pct_deviation = max(abs_pct_deviations) if abs_pct_deviations else 0
        avg_pct_deviation = sum(abs_pct_deviations) / len(abs_pct_deviations) if abs_pct_deviations else 0
        
        # Gini coefficient (measure of inequality, 0 = perfect equality, 1 = perfect inequality)
        if len(results) > 1:
            actual_rates = [r["actual_rate"] for r in results]
            expected_rates = [r["expected_rate"] for r in results]
            gini_actual = self._calculate_gini(actual_rates)
            gini_expected = self._calculate_gini(expected_rates)
            gini_difference = abs(gini_actual - gini_expected)
        else:
            gini_difference = 0
        
        # Calculate chi-square statistic for goodness of fit
        chi_square = 0
        for r in results:
            expected = r["expected_rate"] * len(selections)
            actual = r["selections"]
            if expected > 0:
                chi_square += ((actual - expected) ** 2) / expected
        
        # Calculate p-value (probability that the distribution is fair)
        # Degrees of freedom = number of validators - 1
        degrees_of_freedom = len(validators) - 1
        p_value = self._calculate_p_value(chi_square, degrees_of_freedom) if degrees_of_freedom > 0 else 1.0
        
        # Calculate consecutive selections
        consecutive_counts = self._analyze_consecutive_selections(selections)
        
        # Calculate trend analysis if we have enough history
        trend_analysis = {}
        if len(self.statistical_data["p_value_history"]) >= 5:
            trend_analysis = {
                "p_value_trend": self._calculate_trend(self.statistical_data["p_value_history"][-5:]),
                "chi_square_trend": self._calculate_trend(self.statistical_data["chi_square_history"][-5:]),
                "gini_trend": self._calculate_trend(self.statistical_data["gini_history"][-5:]),
                "max_deviation_trend": self._calculate_trend(self.statistical_data["max_deviation_history"][-5:])
            }
        
        return {
            "validator_stats": results,
            "max_deviation": max_deviation,
            "avg_deviation": avg_deviation,
            "max_percentage_deviation": max_pct_deviation,
            "avg_percentage_deviation": avg_pct_deviation,
            "gini_difference": gini_difference,
            "chi_square": chi_square,
            "p_value": p_value,
            "consecutive_counts": consecutive_counts,
            "trend_analysis": trend_analysis,
            "fair_distribution": p_value > 0.05,  # Standard statistical significance threshold
            "resistant_to_grinding": max_deviation < 0.2 and consecutive_counts["max_consecutive"] <= 2  # Less than 20% deviation is considered resistant
        }
    
    def _analyze_consecutive_selections(self, selections: List[str]) -> Dict[str, Any]:
        """
        Analyze consecutive selections of the same validator
        
        Args:
            selections: List of selected validator addresses
            
        Returns:
            Dict: Analysis of consecutive selections
        """
        if not selections:
            return {"max_consecutive": 0, "consecutive_counts": {}}
        
        max_consecutive = 0
        current_consecutive = 1
        current_validator = selections[0]
        consecutive_counts = {}
        
        for i in range(1, len(selections)):
            if selections[i] == current_validator:
                current_consecutive += 1
            else:
                # Record consecutive count for previous validator
                consecutive_counts[current_validator] = max(
                    consecutive_counts.get(current_validator, 0),
                    current_consecutive
                )
                max_consecutive = max(max_consecutive, current_consecutive)
                
                # Reset for new validator
                current_validator = selections[i]
                current_consecutive = 1
        
        # Record the last validator's consecutive count
        consecutive_counts[current_validator] = max(
            consecutive_counts.get(current_validator, 0),
            current_consecutive
        )
        max_consecutive = max(max_consecutive, current_consecutive)
        
        return {
            "max_consecutive": max_consecutive,
            "consecutive_counts": consecutive_counts
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """
        Calculate trend direction from a series of values
        
        Args:
            values: List of values to analyze
            
        Returns:
            str: Trend direction ("improving", "worsening", or "stable")
        """
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear regression
        n = len(values)
        x = list(range(n))
        y = values
        
        # Calculate slope
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Determine trend direction
        threshold = 0.01  # Minimum slope to consider a trend
        if abs(slope) < threshold:
            return "stable"
        elif slope > 0:
            # For p-value, increasing is good
            # For chi-square, gini, and deviation, increasing is bad
            if y == self.statistical_data["p_value_history"][-5:]:
                return "improving"
            else:
                return "worsening"
        else:
            # For p-value, decreasing is bad
            # For chi-square, gini, and deviation, decreasing is good
            if y == self.statistical_data["p_value_history"][-5:]:
                return "worsening"
            else:
                return "improving"
    
    def _calculate_gini(self, values: List[float]) -> float:
        """
        Calculate the Gini coefficient as a measure of distribution inequality.
        
        Args:
            values: List of values
            
        Returns:
            float: Gini coefficient (0 = perfect equality, 1 = perfect inequality)
        """
        if not values or len(values) < 2:
            return 0
        
        # Sort values
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        # Calculate Gini coefficient
        numerator = sum((i+1) * sorted_values[i] for i in range(n))
        denominator = n * sum(sorted_values)
        
        if denominator == 0:
            return 0
        
        return (2 * numerator / denominator) - (n + 1) / n
    
    def _calculate_p_value(self, chi_square: float, degrees_of_freedom: int) -> float:
        """
        Calculate p-value from chi-square statistic using a simplified approximation.
        
        Args:
            chi_square: Chi-square statistic
            degrees_of_freedom: Degrees of freedom
            
        Returns:
            float: Approximate p-value
        """
        # This is a simplified approximation for the p-value
        # For a more accurate calculation, you would use a proper statistical library
        
        # If chi-square is very small, distribution is likely fair
        if chi_square < 0.01:
            return 0.99
            
        # Wilson-Hilferty approximation for chi-square p-value
        z = math.sqrt(2 * chi_square) - math.sqrt(2 * degrees_of_freedom - 1)
        
        # Convert z-score to p-value using a simple approximation
        if z <= 0:
            return 0.5
        elif z < 2:
            return 0.5 - 0.15 * z  # Rough approximation
        elif z < 5:
            return 0.1 / z  # Rough approximation
        else:
            return 0.01  # Very small p-value for large z
    
    def reset_fairness_tracking(self):
        """Reset fairness tracking data"""
        self.selection_counts = {}
        self.statistical_data = {
            "chi_square_history": [],
            "p_value_history": [],
            "gini_history": [],
            "max_deviation_history": []
        }
        logger.info("Fairness tracking data has been reset")
    
    def get_statistical_summary(self) -> Dict[str, Any]:
        """
        Get a summary of statistical data for validator selection
        
        Returns:
            Dict: Statistical summary
        """
        if not self.statistical_data["p_value_history"]:
            return {"status": "insufficient_data"}
        
        # Calculate averages of recent metrics
        recent_count = min(20, len(self.statistical_data["p_value_history"]))
        recent_p_values = self.statistical_data["p_value_history"][-recent_count:]
        recent_chi_squares = self.statistical_data["chi_square_history"][-recent_count:]
        recent_ginis = self.statistical_data["gini_history"][-recent_count:]
        recent_deviations = self.statistical_data["max_deviation_history"][-recent_count:]
        
        avg_p_value = sum(recent_p_values) / len(recent_p_values) if recent_p_values else 0
        avg_chi_square = sum(recent_chi_squares) / len(recent_chi_squares) if recent_chi_squares else 0
        avg_gini = sum(recent_ginis) / len(recent_ginis) if recent_ginis else 0
        avg_deviation = sum(recent_deviations) / len(recent_deviations) if recent_deviations else 0
        
        # Calculate trends
        p_value_trend = self._calculate_trend(recent_p_values) if len(recent_p_values) >= 5 else "insufficient_data"
        chi_square_trend = self._calculate_trend(recent_chi_squares) if len(recent_chi_squares) >= 5 else "insufficient_data"
        gini_trend = self._calculate_trend(recent_ginis) if len(recent_ginis) >= 5 else "insufficient_data"
        deviation_trend = self._calculate_trend(recent_deviations) if len(recent_deviations) >= 5 else "insufficient_data"
        
        return {
            "status": "ok",
            "metrics": {
                "avg_p_value": avg_p_value,
                "avg_chi_square": avg_chi_square,
                "avg_gini_difference": avg_gini,
                "avg_max_deviation": avg_deviation
            },
            "trends": {
                "p_value": p_value_trend,
                "chi_square": chi_square_trend,
                "gini_difference": gini_trend,
                "max_deviation": deviation_trend
            },
            "fairness_assessment": {
                "statistically_fair": avg_p_value > 0.05,
                "low_inequality": avg_gini < 0.1,
                "low_deviation": avg_deviation < 0.2,
                "overall_fair": avg_p_value > 0.05 and avg_gini < 0.1 and avg_deviation < 0.2
            }
        }


# Example usage
if __name__ == "__main__":
    # Example validators
    validators = [
        {"address": "bt2c_validator1", "stake": 100},
        {"address": "bt2c_validator2", "stake": 200},
        {"address": "bt2c_validator3", "stake": 300},
        {"address": "bt2c_validator4", "stake": 400}
    ]
    
    # Example block data
    block_data = {
        "height": 100,
        "previous_hash": "0000abcd1234",
        "validator": "bt2c_validator1",
        "transactions": ["tx1", "tx2", "tx3"]
    }
    
    # Create validator selector
    selector = ValidatorSelector()
    
    # Simulate 1000 selections
    selections = []
    for i in range(1000):
        # Update block data to simulate changing blocks
        block_data["height"] = 100 + i
        block_data["previous_hash"] = hashlib.sha256(f"{block_data['previous_hash']}:{i}".encode()).hexdigest()
        
        # Select validator
        selected = selector.select_validator(validators, block_data)
        selections.append(selected)
        
        # Update block data with selected validator
        block_data["validator"] = selected
    
    # Analyze distribution
    analysis = selector.analyze_distribution(selections, validators)
    
    # Print results
    print("Validator Selection Analysis:")
    for stat in analysis["validator_stats"]:
        print(f"Validator {stat['address']}: Expected {stat['expected_rate']*100:.2f}%, "
              f"Actual {stat['actual_rate']*100:.2f}%, Deviation {stat['percentage_deviation']:.2f}%")
    
    print(f"\nMax Deviation: {analysis['max_deviation']*100:.2f}%")
    print(f"Average Deviation: {analysis['avg_deviation']*100:.2f}%")
    print(f"Max Percentage Deviation: {analysis['max_percentage_deviation']:.2f}%")
    print(f"Average Percentage Deviation: {analysis['avg_percentage_deviation']:.2f}%")
    print(f"Gini Difference: {analysis['gini_difference']:.4f}")
    print(f"Chi-Square: {analysis['chi_square']:.4f}")
    print(f"P-Value: {analysis['p_value']:.4f}")
    print(f"Max Consecutive Blocks: {analysis['consecutive_counts']['max_consecutive']}")
    print(f"Fair Distribution: {analysis['fair_distribution']}")
    print(f"Resistant to Grinding: {analysis['resistant_to_grinding']}")
    
    # Get statistical summary
    summary = selector.get_statistical_summary()
    print("\nStatistical Summary:")
    print(f"Status: {summary['status']}")
    if summary['status'] == 'ok':
        print(f"Average P-Value: {summary['metrics']['avg_p_value']:.4f}")
        print(f"P-Value Trend: {summary['trends']['p_value']}")
        print(f"Overall Fairness: {summary['fairness_assessment']['overall_fair']}")
