# SmartThings MCP Server

Model Context Protocol (MCP) server for controlling SmartThings devices.

## Quick Start

```bash
# 1. Install
uv pip install -e .

# 2. Create OAuth app (requires SmartThings CLI)
brew install smartthingscommunity/smartthings/smartthings  # or: npm install -g @smartthings/cli
smartthings login
smartthings apps:create  # Select OAuth-In App, save client_id/secret

# 3. Configure
export SMARTTHINGS_CLIENT_ID=your_client_id
export SMARTTHINGS_CLIENT_SECRET=your_client_secret

# 4. Authenticate (opens browser)
python -m smartthings_mcp.oauth_setup

# Done! Tokens auto-refresh every 24 hours
```

**Alternative**: Use Personal Access Token (expires daily)
```bash
export SMARTTHINGS_TOKEN=your_token  # Get from: https://account.smartthings.com/tokens
```

## Authentication Methods

| Method | Setup Time | Token Expiry | Auto-Refresh |
|--------|-----------|--------------|--------------|
| **OAuth** | 5 min (one-time) | 24 hours | ✅ Automatic |
| **PAT** | 1 min | 24 hours | ❌ Manual regeneration |

**Recommendation**: Use OAuth for ongoing use, PAT for quick testing.

## OAuth Setup Details

### Prerequisites
SmartThings CLI is required (web UI discontinued in 2022):
```bash
# macOS
brew install smartthingscommunity/smartthings/smartthings

# npm
npm install -g @smartthings/cli

# Or download: https://github.com/SmartThingsCommunity/smartthings-cli/releases
```

### Create OAuth App
```bash
smartthings login
smartthings apps:create
```

When prompted:
- App type: **OAuth-In App** (API_ONLY)
- Display name: `SmartThings MCP`
- Redirect URI: `http://localhost:8080/callback`
- Scopes: `r:devices:*`, `x:devices:*`, `r:locations:*`

**Save the client_id and client_secret** (shown only once!)

### Run Setup
```bash
export SMARTTHINGS_CLIENT_ID=your_client_id
export SMARTTHINGS_CLIENT_SECRET=your_client_secret
python -m smartthings_mcp.oauth_setup
```

Tokens are saved to `~/.config/smartthings-mcp/tokens.json` and refresh automatically.

## Configuration

The package automatically loads `.env` file if it exists in your project directory.

Create `.env` file:
```bash
SMARTTHINGS_CLIENT_ID=your_client_id
SMARTTHINGS_CLIENT_SECRET=your_client_secret
```

Or use environment variables directly (no .env file needed).

## Troubleshooting

**"OAuth tokens not found"** → Run `python -m smartthings_mcp.oauth_setup`

**Port 8080 in use** → Stop other services or modify redirect URI in OAuth app

**Token refresh fails** → Re-run setup to get new tokens

**PAT expires daily** → Switch to OAuth or regenerate at https://account.smartthings.com/tokens

## License

MIT
