#!/usr/bin/env python3
#
# -*- coding: utf-8 -*-
#
# Copyright (c) 2025 tombraid@snu.ac.kr
# All right reserved.
#

import asyncio
import json
import os
import sys
import traceback
import httpx
from datetime import datetime, timedelta

# Add project root to path to allow module imports
sys.path.append('.')

from sfai25.extra.client import ExtraClient

async def main():
    """
    This script tests all functionalities of the ExtraClient.
    """
    # Load configuration from conf.json
    try:
        conf_path = "sfai25/extra/conf.json"
        with open(conf_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: {conf_path} not found. Please make sure the configuration file exists.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode {conf_path}. Please check the file format.")
        return

    # Create an instance of ExtraClient
    client = ExtraClient(config)

    # Create necessary directories
    os.makedirs("forecasts", exist_ok=True)
    os.makedirs("images", exist_ok=True)

    try:
        # --- 1. Test get_forecast ---
        print("\n[1/4] Getting forecast data...")
        forecast = await client.get_forecast()
        print("-> Forecast data received and saved to forecasts/forecast.json")
        print("\n--- Forecast Data ---")
        print(json.dumps(forecast, indent=4, ensure_ascii=False))
        print("---------------------\n")

        # --- 2. Test get_image ---
        print("\n[2/4] Getting image data...")
        if client.dataids:
            for data_id in client.dataids:
                print(f"- Getting image for data_id: {data_id}...")
                result = await client.get_image(data_id=data_id)
                print(f"-> Image for data_id {data_id} saved to {result['image_path']}")
        else:
            print("-> No dataids_for_camera found in conf.json. Skipping image test.")

        # --- 3. Test post_heartbeat ---
        print("\n[3/4] Posting heartbeat...")
        heartbeat_content = f"Test heartbeat from forecast_test.py at {datetime.now().isoformat(timespec='seconds')}"
        response = await client.post_heartbeat(content=heartbeat_content)
        print(f"-> Heartbeat posted successfully. Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")

        # --- 4. Test post_target ---
        print("\n[4/4] Posting target...")
        target_time = (datetime.now() + timedelta(minutes=10)).isoformat(timespec='seconds')
        target_payload = [{
            "farm_id": 1,
            "temperature": 25.5,
            "humidity": 65.0,
            "CO2": 800.0,
            "VPD": 1.2,
            "targettime": target_time
        }]
        response = await client.post_target(target_payload)
        print(f"-> Target posted successfully. Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")

    except httpx.ConnectTimeout:
        print("\n[Connection Error]")
        print(f"Could not connect to the server at {client.base_url}.")
        print("Please check if the server is running and accessible.")

    except Exception as e:
        print(f"\n[An unexpected error occurred]")
        print(f"Error: {type(e).__name__} - {e}")
        print("\n--- Traceback ---")
        traceback.print_exc()
        print("-------------------")

if __name__ == "__main__":
    asyncio.run(main())
