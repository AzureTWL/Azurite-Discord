# Azurite Bot

A Discord bot gacha system, spesficially built with Danganronp V3's item pool.

NOTE: THIS BOT ITSELF DOES NOT have a currency system. Please use another bot's currency system.

## Features

- 🎲 Gacha system with cooldown
- 🎒 Inventory management with categories
- 🔍 Advanced search functionality with fuzzy matching
- 📦 Item trading between users
- ⚙️ Admin controls for item management
- 📋 Category-based organization
- 🎯 Random item generation
- 📚 Comprehensive command guide

## Setup

1. Clone the repository
2. Install required packages:
   ```bash
   pip install discord.py
   ```
3. Create a `config.json` file with your bot configuration:
   ```json
   {
       "token": "your_bot_token_here",
       "channel_id": your_channel_id, 
       "target_channel_id": your_target_channel_id,
       "target_user_id": your_target_user_id,
       "currency_name": "star tokens"
   }
   ```
4. Edit the `ADMIN_USER_ID` in `azurite.py` to set your admin user ID:
   ```python
   # Hardcoded admin user ID for security
   self.ADMIN_USER_ID = 123456789  # Replace with your actual admin user ID
   ```
5. Run the bot:
   ```bash
   python azurite.py
   ```

## Commands

### Basic Commands
- `.rng` - Roll for a random item (30s cooldown)
- `.inventory` or `.inv` - View your inventory
- `.search` - Search for items
- `.give` - Give an item to another user
- `.guide` - View all available commands

### Inventory Management
- `.inventory @user` - View another user's inventory
- `.inventory --sort id` - Sort inventory by ID
- `.inventory --sort name` - Sort inventory by name
- `.inventory --sort category` - Sort inventory by category (default)

### Search Features
- `.search query` - Search items by description
- `.search --category category` - Search within a category
- `.search --id number` - Search by item ID
- `.search -c category` - Short form for category search
- `.search -i number` - Short form for ID search

### Admin Commands
- `.admin add @user item_id` - Add item to user
- `.admin remove @user item_id` - Remove item from user
- `.admin clear @user` - Clear user's inventory
- `.setcurrency [name]` - Set or view the currency name

### Utility Commands
- `.categories` - List all item categories
- `.random` - Get a random item
- `.random --category category` - Get random item from category

## Special Items

The bot includes two special items that are exclusive to the admin:
- Developer's Toolkit (ID: 8046)
- The Azureblade (ID: 8047)

These items cannot be obtained through normal means, traded, or modified through admin commands.

## File Structure

- `azurite.py` - Main bot code
- `config.json` - Configuration file (create your own)
- `user_items.json` - User inventory data (created automatically)
- `backups/` - Backup directory (created automatically)
- `bot.log` - Log file (created automatically)

## Contributing

Feel free to submit issues and pull requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
