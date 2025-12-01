# Telegram Sticker & Emoji Bot

A Telegram bot that allows users to create both Sticker Packs and Custom Emoji Packs directly from images.

## Features

- **Create Sticker Packs**: Convert images to standard Telegram stickers (512x512).
- **Create Emoji Packs**: Convert images to custom emojis (100x100).
- **Auto-Resizing**: Automatically handles image resizing and formatting requirements.
- **Simple Interface**: Easy-to-use buttons and commands.
- **Informal Style**: The bot communicates in a casual, friendly manner.

## Requirements

- Python 3.11+
- A Telegram Bot Token (from @BotFather)

## Installation

1.  Clone the repository:
    ```bash
    git clone <your-repo-url>
    cd StickCreator_TG
    ```

2.  Install dependencies:
    ```bash
    # Using uv (recommended)
    uv sync
    
    # Or using pip
    pip install -r requirements.txt
    ```

3.  Create a `.env` file in the root directory and add your bot token:
    ```env
    BOT_TOKEN=your_token_here
    ```

## Usage

1.  Run the bot:
    ```bash
    uv run main.py
    ```
2.  Open the bot in Telegram and send `/start`.
3.  Click "➕ Создать новый пак" (Create new pack).
4.  Enter a title for your pack.
5.  Choose the type: "📦 Обычные стикеры" (Regular Stickers) or "😀 Эмодзи пак" (Emoji Pack).
6.  Send an image to add it to the pack!

## Project Structure

- `main.py`: Main bot logic and database handling.
- `stickers.db`: SQLite database for storing pack metadata (not committed).
- `pyproject.toml`: Project dependencies and configuration.

## License

MIT
