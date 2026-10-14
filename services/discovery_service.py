from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

class DiscoveryService:
    def __init__(self):
        # Key: gateway_ip (str) -> dict of { mac_address: client_data }
        self._discovered: Dict[str, Dict[str, Any]] = {}

    def register_live_client(
        self,
        gateway_ip: str,
        mac: str,
        paper_level: float,
        battery: float,
        status: str,
        distance: Optional[float] = None,
        remaining_thickness_cm: Optional[float] = None,
        remaining_thickness_mm: Optional[float] = None,
        estimated_uses: Optional[int] = None,
        raw_data: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Record an active client transmitting to this Gateway.
        Stores in-memory without persisting to database.
        """
        gw_key = gateway_ip.strip()
        mac_key = mac.strip().upper()

        if gw_key not in self._discovered:
            self._discovered[gw_key] = {}

        now_iso = datetime.now(timezone.utc).isoformat()
        client_data = {
            "mac_address": mac_key,
            "gateway_ip": gw_key,
            "distance": round(float(distance), 1) if distance is not None else None,
            "remaining_thickness_cm": round(float(remaining_thickness_cm), 2) if remaining_thickness_cm is not None else None,
            "remaining_thickness_mm": round(float(remaining_thickness_mm), 1) if remaining_thickness_mm is not None else None,
            "estimated_uses": int(estimated_uses) if estimated_uses is not None else None,
            "paper_level": round(float(paper_level), 1),
            "battery": round(float(battery), 1),
            "status": status,
            "last_seen": now_iso,
            "is_saved": False
        }
        self._discovered[gw_key][mac_key] = client_data
        return client_data

    def get_discovered_for_gateway(self, gateway_ip: str) -> List[Dict[str, Any]]:
        """Return list of live discovered clients for a given gateway IP"""
        if not gateway_ip:
            return []
        gw_key = gateway_ip.strip()
        if gw_key not in self._discovered:
            return []
        return list(self._discovered[gw_key].values())

    def get_all_discovered(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return all discovered clients across all gateways"""
        return {
            gw: list(devs.values())
            for gw, devs in self._discovered.items()
        }

    def remove_saved_client(self, mac: str):
        """When a client is officially saved into database, remove it from un-saved list"""
        mac_key = mac.strip().upper()
        for gw, devs in self._discovered.items():
            if mac_key in devs:
                del devs[mac_key]

    def clear_gateway(self, gateway_ip: str):
        gw_key = gateway_ip.strip()
        if gw_key in self._discovered:
            del self._discovered[gw_key]

discovery_service = DiscoveryService()
