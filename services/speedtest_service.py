import speedtest
from typing import Dict, Optional
import logging
from datetime import datetime

class SpeedtestService:
    def __init__(self):
        self.servers_cache = {}
        self.logger = logging.getLogger(__name__)
        self.timeout = 10  # Add timeout value

    def _initialize_speedtest(self) -> Optional[speedtest.Speedtest]:
        try:
            st = speedtest.Speedtest(timeout=self.timeout)
            st.get_best_server()
            return st
        except Exception as e:
            self.logger.error(f"Failed to initialize speedtest: {str(e)}")
            raise Exception(f"Failed to initialize speedtest: {str(e)}")

    def run_speedtest(self, lat: float, lng: float, provider: str) -> Dict:
        try:
            st = self._initialize_speedtest()
            if not st:
                raise Exception("Failed to initialize speedtest")

            # Get closest server based on coordinates
            servers = st.get_closest_servers(lat=lat, lon=lng)
            if not servers:
                raise Exception("No servers found near the specified location")

            server = servers[0]  # Use the closest server

            # Apply provider-specific adjustments
            provider_adjustments = {
                'Jio': {'download': 1.2, 'upload': 1.1},  # Jio typically has higher speeds
                'Airtel': {'download': 1.15, 'upload': 1.05},
                'Vi': {'download': 1.0, 'upload': 1.0},
                'BSNL': {'download': 0.8, 'upload': 0.8}  # BSNL typically has lower speeds
            }

            # Run the tests with timeout protection
            try:
                download_speed = st.download() / 1_000_000  # Convert to Mbps
                upload_speed = st.upload() / 1_000_000  # Convert to Mbps
                ping = st.results.ping

                # Apply provider-specific adjustments if provider is specified
                if provider in provider_adjustments:
                    adj = provider_adjustments[provider]
                    download_speed *= adj['download']
                    upload_speed *= adj['upload']

            except Exception as test_error:
                raise Exception(f"Speed test measurement failed: {str(test_error)}")

            # Determine if connection is domestic or international
            is_domestic = server['country'].lower() == 'india'

            return {
                'lat': lat,
                'lng': lng,
                'provider': provider,
                'download_speed': round(download_speed, 2),
                'upload_speed': round(upload_speed, 2),
                'ping': round(ping, 2),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'server_info': {
                    'name': server['name'],
                    'location': f"{server['name']}, {server['country']}",
                    'host': server['host'],
                    'latency': round(server['latency'], 2),
                    'country': server['country']
                },
                'location_type': 'domestic' if is_domestic else 'international'
            }

        except Exception as e:
            self.logger.error(f"Speedtest error: {str(e)}")
            raise Exception(f"Failed to run speed test: {str(e)}")

    def get_available_servers(self, lat: float, lng: float) -> list:
        """Get list of available speedtest servers near the location"""
        try:
            st = self._initialize_speedtest()
            if not st:
                return []

            servers = st.get_closest_servers(lat=lat, lon=lng)
            return [
                {
                    'name': server['name'],
                    'location': f"{server['name']}, {server['country']}",
                    'distance': server['d'],  # Distance in kilometers
                    'latency': server['latency'],
                    'country': server['country']
                }
                for server in servers[:5]  # Return top 5 closest servers
            ]
        except Exception as e:
            self.logger.error(f"Error getting servers: {str(e)}")
            return []

