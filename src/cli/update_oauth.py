#!/usr/bin/env python3
"""
Update SmartThings app OAuth settings using the SmartThings CLI.

This script:
1. Loads app ID and redirect URI from .env
2. Reads clientName and scope from temp.json
3. Executes `smartthings apps:oauth:update` with the merged configuration
"""

import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv


def load_template(template_path: str) -> dict:
    """Load OAuth template from JSON file."""
    try:
        with open(template_path, 'r') as f:
            template = json.load(f)

        # Validate required fields
        if not template.get("clientName"):
            print(f"Error: Template missing required 'clientName' field")
            sys.exit(1)
        if not template.get("scope"):
            print(f"Error: Template missing required 'scope' field")
            sys.exit(1)

        return template
    except FileNotFoundError:
        print(f"Error: Template file not found: {template_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in template file: {e}")
        sys.exit(1)


def build_oauth_config(template: dict, redirect_uri: str) -> dict:
    """Build OAuth configuration by merging template with redirect URI."""
    return {
        "clientName": template.get("clientName", ""),
        "scope": template.get("scope", []),
        "redirectUris": [redirect_uri]
    }


def check_smartthings_cli() -> bool:
    """Check if SmartThings CLI is installed."""
    try:
        result = subprocess.run(
            ["smartthings", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def update_oauth(app_id: str, config: dict, dry_run: bool = False, verbose: bool = False) -> bool:
    """
    Update SmartThings app OAuth settings.

    Args:
        app_id: SmartThings app ID
        config: OAuth configuration dict
        dry_run: If True, show what would be updated without applying
        verbose: If True, show detailed output

    Returns:
        True if successful, False otherwise
    """
    # Create temporary config file with secure permissions
    fd, temp_file = tempfile.mkstemp(suffix='.json')
    try:
        # Set secure permissions (0o600 - read/write for owner only)
        os.chmod(temp_file, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception:
        os.close(fd)
        raise

    try:
        if verbose:
            print(f"\nConfiguration to be applied:")
            print(json.dumps(config, indent=2))
            print(f"\nTemporary config file: {temp_file}")

        # Build command
        cmd = ["smartthings", "apps:oauth:update", app_id, "-i", temp_file, "-j"]

        if dry_run:
            print("\nDry run mode - showing command that would be executed:")
            print(f"  {' '.join(cmd)}")
            print(f"\nConfiguration:")
            print(json.dumps(config, indent=2))
            return True

        if verbose:
            print(f"\nExecuting: {' '.join(cmd)}")

        # Execute command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("\nOAuth settings updated successfully!")
            if verbose and result.stdout:
                print("\nOutput:")
                print(result.stdout)
            return True
        else:
            print(f"\nError: Failed to update OAuth settings (exit code: {result.returncode})")
            if result.stderr:
                print(f"Error output:\n{result.stderr}")
            if result.stdout:
                print(f"Standard output:\n{result.stdout}")
            return False

    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file)
            if verbose:
                print(f"\nCleaned up temporary file: {temp_file}")
        except Exception as e:
            if verbose:
                print(f"\nWarning: Failed to clean up temporary file: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Update SmartThings app OAuth settings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use environment variables from .env
  %(prog)s

  # Override app ID
  %(prog)s --app-id 38e7355b-74a8-4ca1-aadd-941d1dcdbf9d

  # Dry run to preview changes
  %(prog)s --dry-run

  # Verbose output
  %(prog)s --verbose
"""
    )

    parser.add_argument(
        '--app-id',
        help='SmartThings app ID (overrides SMARTTHINGS_APP_ID from .env)'
    )
    parser.add_argument(
        '--redirect-uri',
        help='OAuth redirect URI (overrides SMARTTHINGS_REDIRECT_URI from .env)'
    )
    parser.add_argument(
        '--template',
        default='temp.json',
        help='Template JSON file (default: temp.json)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without applying changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output'
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Get app ID
    app_id = args.app_id or os.getenv('SMARTTHINGS_APP_ID')
    if not app_id:
        print("Error: SMARTTHINGS_APP_ID not set")
        print("Please set it in .env or use --app-id")
        sys.exit(1)

    # Get redirect URI
    redirect_uri = args.redirect_uri or os.getenv('SMARTTHINGS_REDIRECT_URI')
    if not redirect_uri:
        print("Error: SMARTTHINGS_REDIRECT_URI not set")
        print("Please set it in .env or use --redirect-uri")
        sys.exit(1)

    # Check SmartThings CLI
    if not check_smartthings_cli():
        print("Error: SmartThings CLI not found")
        print("Please install it from: https://github.com/SmartThingsCommunity/smartthings-cli")
        sys.exit(1)

    # Load template
    template = load_template(args.template)

    # Build OAuth config
    config = build_oauth_config(template, redirect_uri)

    # Display info
    print("SmartThings OAuth Update")
    print("=" * 40)
    print(f"App ID: {app_id}")
    print(f"Redirect URI: {redirect_uri}")
    print(f"Template: {args.template}")
    if args.dry_run:
        print("Mode: DRY RUN")

    # Update OAuth settings
    success = update_oauth(app_id, config, args.dry_run, args.verbose)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
