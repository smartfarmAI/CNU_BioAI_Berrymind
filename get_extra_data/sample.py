import asyncio
import json
import os
from datetime import datetime, timedelta
from client import ExtraClient

async def main():
    """
    This is a sample script to test the ExtraClient class.
    It reads the configuration from conf.json, creates an ExtraClient instance,
    and then calls the get_forecast and get_image methods.
    """
    # Load configuration from conf.json
    try:
        conf_path = "conf.json"
        with open(conf_path) as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: conf.json not found. Please make sure the configuration file exists.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode conf.json. Please check the file format.")
        return

    # Create an instance of ExtraClient
    client = ExtraClient(config)

    # Create forecasts directory if it doesn't exist
    if not os.path.exists("forecasts"):
        os.makedirs("forecasts")

    # Test get_forecast
    try:
        print("Getting forecast data...")
        forecast = await client.get_forecast()
        print("Forecast data received and saved to forecasts/forecast.json")
        # You can uncomment the line below to print the forecast data
        # print(json.dumps(forecast, indent=4))
    except Exception as e:
        print(f"Error getting forecast: {e}")

    # Test get_image for each dataid
    if client.dataids:
        for data_id in client.dataids:
            try:
                print(f"Getting image for data_id: {data_id}...")
                result = await client.get_image(data_id=data_id)
                print(f"Image for data_id {data_id} received and saved to {result['image_path']}")
                print(f"Image filename: {result['filename']}")
            except Exception as e:
                if "404" in str(e) or "No image found" in str(e):
                    print(f"No image found for data_id {data_id} (this is expected if no images are uploaded yet)")
                elif "400" in str(e) or "Invalid image path" in str(e):
                    print(f"Invalid image path for data_id {data_id} (database entry exists but file is missing)")
                else:
                    print(f"Error getting image for data_id {data_id}: {e}")
    else:
        print("No dataids_for_camera found in the configuration file.")
    """
    # Test post_heartbeat
    try:
        print("Posting heartbeat...")
        response = await client.post_heartbeat(
            content="This is a test heartbeat from extra client: " + str(datetime.now().isoformat(timespec='seconds'))
        )
        print(f"Heartbeat posted successfully. Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error posting heartbeat: {e}")

    # Test post_target
    try:
        print("Posting target...")
        target_time = (datetime.now() + timedelta(minutes=10)).isoformat(timespec='seconds')
        target_payload = [
            {
                "farm_id": 2,
                "temperature": 25.5,
                "humidity": 65.0,
                "CO2": 800.0,
                "VPD": 1.2,
                "targettime": target_time
            }
        ]
        response = await client.post_target(target_payload)
        print(f"Target posted successfully. Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error posting target: {e}")
    """

if __name__ == "__main__":
    # To run this sample, you would typically execute `python sample.py` in your terminal.
    # This will run the asyncio event loop and execute the main coroutine.
    asyncio.run(main())