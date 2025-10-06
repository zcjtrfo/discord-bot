# Use Python 3.12 explicitly (which includes audioop)
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy your files into the container
COPY . .

# Prevent Discord.py from trying to load audio/voice modules
ENV DISCORD_NO_AUDIO=1

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run your bot
CMD ["python", "bot.py"]
