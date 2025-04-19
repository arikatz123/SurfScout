import os
import streamlit as st
import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
WILLYWEATHER_API_KEY = os.getenv("WILLYWEATHER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
openai = OpenAI(api_key=OPENAI_API_KEY)

def search_beach(beach_name):
    """Search for a beach in the WillyWeather API"""
    # Updated URL format based on WillyWeather API documentation
    url = f"https://api.willyweather.com.au/v2/{WILLYWEATHER_API_KEY}/search.json"
    params = {
        "query": beach_name,
        "limit": 5
        # Removed 'types' parameter as it's not supported according to API error
    }
    
    try:
        # No need to display this debug message in production
        # st.write(f"Searching for: {beach_name}")
        
        # Add headers for API authentication
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Debug the URL we're calling
        debug_url = f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        # st.info(f"Calling Search API: {debug_url}")
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return []
            
        # If response is too small, it might indicate an auth or format issue    
        if len(response.text) < 50:
            st.warning(f"Unusually small search API response: {response.text}")
            
        data = response.json()
        
        # Check response format - WillyWeather API returns a direct list of locations
        if isinstance(data, list):
            # The API directly returns a list of locations
            locations = data
        elif "search" in data:
            # Fall back to old format if present
            locations = data["search"]
        else:
            st.error(f"Unexpected API response format: {data}")
            return []
            
        # Filter for Australian locations - most locations should be in Australia already
        # but we can filter by checking region, state, or timeZone
        australian_locations = [loc for loc in locations 
                              if (loc.get("state") in ["NSW", "QLD", "VIC", "SA", "WA", "TAS", "NT", "ACT"] or
                                 "australia" in loc.get("timeZone", "").lower())]
        
        return australian_locations
    except requests.exceptions.RequestException as e:
        st.error(f"Error searching for beach: {str(e)}")
        return []

def get_surf_conditions(location_id):
    """Get surf conditions (tide, swell, wind) for a location"""
    url = f"https://api.willyweather.com.au/v2/{WILLYWEATHER_API_KEY}/locations/{location_id}/weather.json"
    params = {
        "forecasts": "tides,wind,swell",  # API expects comma-separated string, not list
        "days": 1
    }
    
    try:
        # Add headers for API authentication
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Debug the URL we're calling
        debug_url = f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        # st.info(f"Calling API: {debug_url}")
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code != 200:
            st.error(f"Weather API Error: {response.status_code} - {response.text}")
            return None
            
        # If response is too small, it might indicate an auth or format issue
        if len(response.text) < 100:
            st.warning(f"Unusually small API response, might indicate an issue: {response.text}")
            
        data = response.json()
        
        # Debug data structure if needed
        # st.write("API Response Structure:")
        # st.json(data)
        
        # Check if we have valid data
        if not isinstance(data, dict) or "forecasts" not in data:
            st.error("Unexpected weather API response format. Could not find forecast data.")
            st.info("Response data structure:")
            st.json(data)
            return None
        
        # Extract tide information
        tides_data = data.get("forecasts", {}).get("tides", {})
        tides = []
        if tides_data and "days" in tides_data and tides_data["days"]:
            tides = tides_data["days"][0].get("entries", [])
        
        current_tide = None
        tide_type = "Unknown"
        if tides:
            # Get closest tide information to current time
            current_tide = tides[0].get("height")
            tide_type = tides[0].get("type", "Unknown")
        
        # Extract wind information
        wind_entries = []
        wind_data = data.get("forecasts", {}).get("wind", {})
        if wind_data and "days" in wind_data and wind_data["days"]:
            wind_entries = wind_data["days"][0].get("entries", [])
        
        current_wind = None
        wind_direction = None
        if wind_entries:
            # Get current wind information
            current_wind = wind_entries[0].get("speed")
            wind_direction = wind_entries[0].get("direction")
        
        # Extract swell information
        swell_entries = []
        swell_data = data.get("forecasts", {}).get("swell", {})
        if swell_data and "days" in swell_data and swell_data["days"]:
            swell_entries = swell_data["days"][0].get("entries", [])
        
        current_swell = None
        swell_direction = None
        if swell_entries:
            # Get current swell information
            current_swell = swell_entries[0].get("height")
            swell_direction = swell_entries[0].get("direction")
        
        # Create a structured response
        conditions = {
            "tide": {
                "height": current_tide if current_tide is not None else 0,
                "type": tide_type
            },
            "wind": {
                "speed": current_wind if current_wind is not None else 0,
                "direction": wind_direction if wind_direction is not None else 0
            },
            "swell": {
                "height": current_swell if current_swell is not None else 0,
                "direction": swell_direction if swell_direction is not None else 0
            }
        }
        
        return conditions
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching surf conditions: {str(e)}")
        return None

def assess_surf_quality(conditions, beach_name):
    """Assess surf quality using OpenAI's GPT-4o model"""
    if not OPENAI_API_KEY:
        st.error("OpenAI API key not found. Please add it to your .env file as OPENAI_API_KEY.")
        return {"score": None, "explanation": "OpenAI API key is required for surf quality assessment."}
    
    try:
        # Detailed prompt for ChatGPT to evaluate surf conditions
        prompt = (
            f"You are an expert surfer with deep knowledge of Australian surf conditions. "
            f"Please analyze the following surf conditions for {beach_name}:\n\n"
            f"Tide: {conditions['tide']['height']} meters, type: {conditions['tide']['type']}\n"
            f"Wind: {conditions['wind']['speed']} km/h, direction: {conditions['wind']['direction']}°\n"
            f"Swell: {conditions['swell']['height']} meters, direction: {conditions['swell']['direction']}°\n\n"
            f"Based on these conditions, give me a surf quality score from 0-10 (0 being terrible, 10 being perfect) "
            f"and a one-paragraph explanation justifying the score. Consider how these conditions affect wave quality, "
            f"ride-ability, and overall surf experience. Reply in JSON format with keys 'score' and 'explanation'."
        )
        
        # Here's the actual API call to OpenAI
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": "You are a surf conditions expert focusing on Australian beaches."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}  # Ensures we get a valid JSON response
        )
        
        # Processing the response
        result = response.choices[0].message.content
        import json
        surf_assessment = json.loads(result)
        
        return surf_assessment
    except Exception as e:
        error_message = str(e)
        if "429" in error_message or "quota" in error_message.lower():
            st.error("OpenAI API quota exceeded. Please check your billing details or try again later.")
            st.warning("Your OpenAI API key has reached its usage limit. Please visit https://platform.openai.com/ to check your usage and billing settings.")
        else:
            st.error(f"Error accessing OpenAI API: {error_message}")
        
        return {"score": None, "explanation": "Could not assess surf quality due to an error with the OpenAI API."}

def main():
    st.title("🏄‍♂️ Surf Quality Checker")
    st.write("Find out if it's worth going for a surf at your favorite Australian beach.")
    
    # Check if API keys are available
    if not WILLYWEATHER_API_KEY:
        st.error("WillyWeather API key not found. Please add it to your .env file as WILLYWEATHER_API_KEY.")
        return
    
    if not OPENAI_API_KEY:
        st.error("OpenAI API key not found. Please add it to your .env file as OPENAI_API_KEY.")
        return
    
    # Input for beach name
    beach_name = st.text_input("Enter an Australian beach name:")
    
    if beach_name:
        with st.spinner("Searching for beach..."):
            locations = search_beach(beach_name)
        
        if not locations:
            st.warning(f"No Australian beaches found with the name '{beach_name}'. Please try another name.")
        else:
            # Create a list of location names
            location_names = [f"{loc['name']}, {loc['region']}" for loc in locations]
            
            # Let user select a location
            selected_location = st.selectbox("Select a beach:", location_names)
            
            if st.button("Check Surf Quality"):
                # Find the selected location
                selected_idx = location_names.index(selected_location)
                location_id = locations[selected_idx]["id"]
                
                with st.spinner("Fetching surf conditions..."):
                    conditions = get_surf_conditions(location_id)
                
                if conditions:
                    with st.spinner("Analyzing surf quality..."):
                        assessment = assess_surf_quality(conditions, selected_location)
                    
                    if assessment["score"] is not None:
                        # Display the results
                        st.header("Surf Quality Assessment")
                        
                        # Display score with emoji indicators
                        score = float(assessment["score"])
                        
                        if score >= 7:
                            emoji = "🔥"
                        elif score >= 4:
                            emoji = "🙂"
                        else:
                            emoji = "👎"
                        
                        st.subheader(f"Score: {score}/10 {emoji}")
                        st.write(f"**Why:** {assessment['explanation']}")
                        
                        # Display surf conditions
                        st.subheader("Current Conditions")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Tide", f"{conditions['tide']['height']} m")
                        with col2:
                            st.metric("Wind", f"{conditions['wind']['speed']} km/h")
                        with col3:
                            st.metric("Swell", f"{conditions['swell']['height']} m")

if __name__ == "__main__":
    main()
