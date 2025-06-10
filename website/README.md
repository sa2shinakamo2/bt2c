# bit2coin Website

The official website for the bit2coin project, a sustainable proof-of-stake blockchain platform.

## Deployment to bit2co.net

### Prerequisites
1. Access to Squarespace domain management for bit2co.net
2. Node.js and npm installed
3. Basic knowledge of web deployment

### Deployment Steps

1. **Prepare Files**
   ```bash
   # Install dependencies
   npm install
   
   # Build and optimize assets
   npm run build
   ```

2. **Configure Domain on Squarespace**
   - Log in to your Squarespace account
   - Go to Domains settings
   - Point bit2co.net to your hosting provider
   - Add necessary DNS records

3. **Deploy Static Files**
   - Upload all files from the `website` directory to your hosting provider
   - Ensure all paths in HTML files are relative or pointing to the correct domain
   - Set up proper MIME types for .css and .js files
   - Enable HTTPS for secure connections

4. **API Setup**
   - Deploy the API server (api.py) to a separate subdomain (api.bit2co.net)
   - Configure CORS to allow requests from bit2co.net
   - Set up SSL certificate for the API subdomain

5. **Post-Deployment**
   - Verify all pages load correctly
   - Test all API endpoints
   - Check mobile responsiveness
   - Validate SSL certificates

## Development

To run the website locally:

```bash
# Install dependencies
npm install

# Start the development server
node server.js

# In a separate terminal, start the API server
python api.py
```

The website will be available at http://localhost:3000

## File Structure

```
website/
├── index.html          # Homepage
├── validators.html     # Validator information
├── explorer.html      # Blockchain explorer
├── docs.html         # Documentation
├── wallet.html       # Wallet interface
├── css/             # Stylesheets
├── js/              # JavaScript files
├── images/          # Image assets
└── api.py           # API server
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

Copyright © 2025 bit2coin. All rights reserved.
