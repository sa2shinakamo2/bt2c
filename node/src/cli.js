#!/usr/bin/env node
const { Wallet } = require('./wallet');
const { Blockchain } = require('./blockchain');
const { Validator } = require('./validator');
const prompt = require('prompt-sync')();

const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');

const argv = yargs(hideBin(process.argv))
    .command('create-wallet', 'Create a new wallet', {}, (argv) => {
        console.log('Creating a new secure wallet...');
        console.log('Please enter a strong password (min 8 characters):');
        const password = prompt('Password: ');
        
        if (password.length < 8) {
            console.error('Password must be at least 8 characters long');
            return;
        }

        const wallet = new Wallet();
        const backupPhrase = wallet.generateBackupPhrase();
        const walletData = wallet.save(password);

        console.log('\nWallet created successfully!');
        console.log('Address:', walletData.address);
        console.log('Public Key:', walletData.publicKey);
        console.log('\nIMPORTANT: Write down your backup phrase and keep it safe:');
        console.log(backupPhrase);
        console.log('\nNEVER share your backup phrase or password with anyone!');
    })
    .command('load-wallet', 'Load an existing wallet', {
        file: {
            description: 'wallet file name',
            alias: 'f',
            type: 'string',
            default: 'wallet.json'
        }
    }, (argv) => {
        console.log('Enter your wallet password:');
        const password = prompt('Password: ');
        
        const wallet = Wallet.load(password, argv.file);
        if (wallet) {
            console.log('\nWallet loaded successfully!');
            console.log('Address:', wallet.getAddress());
            console.log('Public Key:', wallet.publicKey);
        }
    })
    .command('balance', 'Check wallet balance', {
        address: {
            description: 'wallet address',
            alias: 'a',
            type: 'string',
            demandOption: true
        }
    }, (argv) => {
        const blockchain = new Blockchain();
        const balance = wallet.getBalance(blockchain);
        console.log(`Balance for ${argv.address}: ${balance} BT2C`);
    })
    .command('start-validator', 'Start validating blocks', {
        wallet: {
            description: 'wallet file name',
            alias: 'w',
            type: 'string',
            default: 'wallet.json'
        }
    }, (argv) => {
        console.log('Enter your wallet password:');
        const password = prompt('Password: ');
        
        const wallet = Wallet.load(password, argv.wallet);
        if (!wallet) return;

        const blockchain = new Blockchain();
        const validator = new Validator(blockchain);
        validator.setStake(1); // Set minimum stake
        validator.start();
    })
    .help()
    .argv;
