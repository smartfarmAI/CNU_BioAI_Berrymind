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
from unittest.mock import AsyncMock, MagicMock

# Add project root to path to allow module imports
sys.path.append('.')

from sfai25.extra.client import ExtraClient

async def main():
    """
    This script tests all functionalities of the ExtraClient using a mock object.
    """
    # --- Mocking Setup ---
    # Create a mock ExtraClient object
    mock_client = AsyncMock(spec=ExtraClient)

    # Configure mock for get_forecast
    mock_forecast_data = {
        "Weather": "Clear",
        "Temperature": "25.5 C",
        "Humidity": "60%",
        "ForecastTime": datetime.now().isoformat()
    }
    mock_client.get_forecast.return_value = mock_forecast_data

    # Configure mock for get_image
    mock_image_result = {
        'image_path': 'images/mock_image_10003210.png',
        'filename': 'mock_image_10003210.png'
    }
    mock_client.get_image.return_value = mock_image_result
    # To simulate having dataids in the config
    mock_client.dataids = [10003210, 10003310]

    # Configure mock for post_heartbeat and post_target
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "message": "Mock data received"}
    mock_client.post_heartbeat.return_value = mock_response
    mock_client.post_target.return_value = mock_response

    # Use the mock client instead of the real one
    client = mock_client

    # Create necessary directories
    os.makedirs("forecasts", exist_ok=True)
    os.makedirs("images", exist_ok=True)

    try:
        # --- 1. Test get_forecast ---
        print("\n[1/4] Getting forecast data (from mock)...")
        forecast = await client.get_forecast()
        # In a real scenario, this would save to a file. We'll just print.
        print("-> Mock forecast data received.")
        print("\n--- Forecast Data ---")
        print(json.dumps(forecast, indent=4, ensure_ascii=False))
        print("---------------------\n")

        # --- 2. Test get_image ---
        print("\n[2/4] Getting image data (from mock)...")
        if client.dataids:
            for data_id in client.dataids:
                print(f"- Getting image for data_id: {data_id}...")
                result = await client.get_image(data_id=data_id)
                print(f"-> Mock image data for data_id {data_id} received. Path: {result['image_path']}")
        else:
            print("-> No dataids_for_camera found in conf.json. Skipping image test.")

        # --- 3. Test post_heartbeat ---
        print("\n[3/4] Posting heartbeat (to mock)...")
        heartbeat_content = f"Test heartbeat from forecast_test.py at {datetime.now().isoformat(timespec='seconds')}"
        response = await client.post_heartbeat(content=heartbeat_content)
        print(f"-> Mock heartbeat posted successfully. Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")

        # --- 4. Test post_target ---
        print("\n[4/4] Posting target (to mock)...")
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
        print(f"-> Mock target posted successfully. Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")

    except Exception as e:
        print(f"\n[An unexpected error occurred during mock test]")
        print(f"Error: {type(e).__name__} - {e}")
        print("\n--- Traceback ---")
        traceback.print_exc()
        print("-------------------")

if __name__ == "__main__":
    asyncio.run(main())
