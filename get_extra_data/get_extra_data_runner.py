from apscheduler.schedulers.blocking import BlockingScheduler
from client import ExtraClient
import os, json
import asyncio

# Load configuration from conf.json
try:
    conf_path = "conf.json"
    with open(conf_path) as f:
        config = json.load(f)
except FileNotFoundError:
    print("Error: conf.json not found. Please make sure the configuration file exists.")
except json.JSONDecodeError:
    print("Error: Could not decode conf.json. Please check the file format.")

# Create an instance of ExtraClient
client = ExtraClient(config)


def get_image_job():
    # Test get_image for each dataid
    if client.dataids:
        for data_id in client.dataids:
            try:
                print(f"Getting image for data_id: {data_id}...")
                result = asyncio.run(client.get_image(data_id=data_id))
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
    

def get_forecast_job():
    # Create forecasts directory if it doesn't exist
    if not os.path.exists("forecasts"):
        os.makedirs("forecasts")

    # Test get_forecast
    try:
        print("Getting forecast data...")
        asyncio.run(client.get_forecast())
        print("Forecast data received and saved to forecasts/forecast.json")
        # You can uncomment the line below to print the forecast data
        # print(json.dumps(forecast, indent=4))
    except Exception as e:
        print(f"Error getting forecast: {e}")
    
sched = BlockingScheduler()

# 이미지 오전 10시 , 15시
sched.add_job(get_image_job, "cron", hour=10, minute=5)
sched.add_job(get_image_job, "cron", hour=15, minute=5)

# 기상 3시간 마다
sched.add_job(get_forecast_job, "interval", hours=3)

sched.start()
