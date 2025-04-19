# Surf Quality Checker

A simple Streamlit application that tells you if it's worth going for a surf at Australian beaches.

## How it works

1. Enter an Australian beach name
2. The app fetches current tide, swell, and wind data from WillyWeather
3. OpenAI analyzes the conditions and provides a surf quality score (0-10)
4. View the score and a brief explanation of why those conditions are good/bad for surfing

## Setup Instructions

1. Clone this repository
2. Install the required packages:
   ```
   pip install streamlit python-dotenv requests openai
   ```
3. Create a `.env` file in the root directory with the following API keys:
   ```
   WILLYWEATHER_API_KEY=your_willyweather_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```
   - Get a WillyWeather API key from: https://www.willyweather.com.au/info/api.html
   - Get an OpenAI API key from: https://platform.openai.com/api-keys

4. Run the application:
   ```
   streamlit run app.py
   ```

## Features

- Search for any Australian beach
- Real-time surf condition data (tide, wind, swell)
- AI-powered surf quality assessment
- Simple, easy-to-use interface

## Notes

- This app only works with Australian beaches as it uses the WillyWeather API
- The free tier of the WillyWeather API has usage limits
