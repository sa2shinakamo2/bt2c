#!/usr/bin/env python3
"""Script to optimize BT2C and run tests."""

import asyncio
import subprocess
import sys
import time
import structlog
from typing import List, Tuple
import os

logger = structlog.get_logger()

class OptimizationRunner:
    """Runs optimization and tests for BT2C."""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.start_time = time.time()

    async def run(self):
        """Run all optimizations and tests."""
        try:
            logger.info("starting_optimization")
            
            # Run code quality checks
            await self.run_code_quality()
            
            # Run security checks
            await self.run_security_checks()
            
            # Run tests
            await self.run_tests()
            
            # Run performance checks
            await self.run_performance_checks()
            
            duration = time.time() - self.start_time
            logger.info("optimization_complete", duration=f"{duration:.2f}s")
            
        except Exception as e:
            logger.error("optimization_failed", error=str(e))
            sys.exit(1)

    async def run_command(self, cmd: List[str], cwd: str = None) -> Tuple[int, str]:
        """Run a command and return exit code and output."""
        try:
            cwd = cwd or self.project_root
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()
            
            if process.returncode != 0:
                logger.warning(
                    "command_failed",
                    cmd=" ".join(cmd),
                    output=output
                )
            
            return process.returncode, output
        
        except Exception as e:
            logger.error(
                "command_error",
                cmd=" ".join(cmd),
                error=str(e)
            )
            return 1, str(e)

    async def run_code_quality(self):
        """Run code quality checks."""
        logger.info("running_code_quality_checks")
        
        # Run black
        code, output = await self.run_command(["black", "."])
        if code != 0:
            raise Exception("Black formatting failed")
        
        # Run isort
        code, output = await self.run_command(["isort", "."])
        if code != 0:
            raise Exception("Import sorting failed")
        
        # Run mypy
        code, output = await self.run_command(["mypy", "."])
        if code != 0:
            raise Exception("Type checking failed")
        
        logger.info("code_quality_checks_passed")

    async def run_security_checks(self):
        """Run security checks."""
        logger.info("running_security_checks")
        
        # Run bandit
        code, output = await self.run_command(["bandit", "-r", "."])
        if code != 0:
            raise Exception("Security check failed")
        
        # Run safety
        code, output = await self.run_command(["safety", "check"])
        if code != 0:
            logger.warning("dependency_security_issues", output=output)
        
        logger.info("security_checks_passed")

    async def run_tests(self):
        """Run all tests."""
        logger.info("running_tests")
        
        # Run pytest with coverage
        code, output = await self.run_command([
            "pytest",
            "--cov=.",
            "--cov-report=xml",
            "--cov-report=term-missing"
        ])
        if code != 0:
            raise Exception("Tests failed")
        
        logger.info("tests_passed")

    async def run_performance_checks(self):
        """Run performance checks."""
        logger.info("running_performance_checks")
        
        # Run locust load tests
        code, output = await self.run_command([
            "locust",
            "--headless",
            "-f", "tests/locustfile.py",
            "--users", "100",
            "--spawn-rate", "10",
            "--run-time", "30s"
        ])
        if code != 0:
            logger.warning("load_test_issues", output=output)
        
        logger.info("performance_checks_complete")

def main():
    """Main entry point."""
    runner = OptimizationRunner()
    asyncio.run(runner.run())

if __name__ == "__main__":
    main()
