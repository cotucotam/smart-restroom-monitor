import argparse
import random
import time
import sys
import httpx
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Local imports for direct seed capability
from seed_demo import seed_demo_toilets_and_devices
from database import SessionLocal
from models import Gateway, Device

def parse_args():
    parser = argparse.ArgumentParser(description="Trình mô phỏng gửi dữ liệu từ Gateway ESP32 lên Server")
    parser.add_argument("--server", type=str, default="http://127.0.0.1:8000", help="Địa chỉ server FastAPI")
    parser.add_argument("--api-key", type=str, default="airport-gateway-secret-api-key-2026", help="X-API-Key để xác thực")
    parser.add_argument("--interval", type=int, default=5, help="Chu kỳ gửi báo cáo (giây)")
    parser.add_argument("--seed", action="store_true", help="Seed dữ liệu mẫu ban đầu trước khi chạy")
    return parser.parse_args()

def load_gateway_devices():
    """Load all registered gateways and their devices from database"""
    db = SessionLocal()
    data = []
    try:
        gateways = db.query(Gateway).all()
        for gw in gateways:
            devices = []
            for dev in gw.devices:
                devices.append({
                    "mac": dev.mac_address,
                    "paper_level": float(dev.paper_level),
                    "battery": float(dev.battery),
                    "label": dev.label,
                    "offline_until_cycle": 0
                })
            # If gateway has no devices yet, create 2-4 simulated devices
            if not devices:
                for i in range(1, random.randint(3, 5)):
                    mac = f"AA:BB:CC:{gw.id:02X}:{i:02X}:01"
                    devices.append({
                        "mac": mac,
                        "paper_level": float(random.randint(60, 95)),
                        "battery": float(random.randint(90, 100)),
                        "label": f"Cabin {i}",
                        "offline_until_cycle": 0
                    })
            data.append({
                "ip": gw.ip_address,
                "devices": devices
            })
    finally:
        db.close()
    return data

def main():
    args = parse_args()

    if args.seed:
        print("[Simulator] Seeding demo airports, terminals, floors, toilets & devices...")
        seed_demo_toilets_and_devices()
        print("[Simulator] Seeding complete!")

    gateways_data = load_gateway_devices()
    if not gateways_data:
        print("[Simulator] Chưa có Gateway nào trong cơ sở dữ liệu. Chạy lại với cờ --seed để tạo tự động:")
        print("    python simulator.py --seed")
        sys.exit(1)

    print("=" * 60)
    print(f"AIRPORT RESTROOM TELEMETRY SIMULATOR")
    print(f"Server Target : {args.server}")
    print(f"Report Period : {args.interval}s")
    print(f"Gateways      : {len(gateways_data)}")
    total_devs = sum(len(gw['devices']) for gw in gateways_data)
    print(f"Total Devices : {total_devs}")
    print("=" * 60)

    url = f"{args.server.rstrip('/')}/api/gateway/report"
    headers = {
        "X-API-Key": args.api_key,
        "Content-Type": "application/json"
    }

    cycle = 0
    with httpx.Client(timeout=10.0) as client:
        while True:
            cycle += 1
            now_str = datetime.now().strftime("%H:%M:%S")
            print(f"\n[Cycle #{cycle} @ {now_str}] Bắt đầu gửi báo cáo từ {len(gateways_data)} Gateways...")

            for gw in gateways_data:
                active_devices = []
                for dev in gw["devices"]:
                    # Check if device is simulating offline outage
                    if cycle < dev["offline_until_cycle"]:
                        # Device is temporarily offline, do not send report
                        continue

                    # Random chance (2%) to initiate an offline period (lasts ~26 cycles = ~130s to exceed 120s timeout)
                    if random.random() < 0.02 and dev["offline_until_cycle"] <= cycle:
                        dev["offline_until_cycle"] = cycle + int(130 / max(1, args.interval))
                        print(f"  [Sim OFFLINE] {gw['ip']} -> {dev['label']} ({dev['mac']}) bắt đầu ngắt kết nối trong ~130s...")
                        continue

                    # Decrement paper level gradually (0.5% - 2.0%)
                    reduction = random.uniform(0.5, 2.0)
                    dev["paper_level"] = max(0.0, dev["paper_level"] - reduction)

                    # If paper <= 5%, 60% chance janitor refills to 100%
                    if dev["paper_level"] <= 5.0 and random.random() < 0.6:
                        dev["paper_level"] = 100.0
                        print(f"  [Refilled] {gw['ip']} -> {dev['label']} vừa được nhân viên bổ sung cuộn giấy mới (100%)!")

                    # Battery drains very slowly
                    if random.random() < 0.2:
                        dev["battery"] = max(10.0, dev["battery"] - 0.1)

                    active_devices.append({
                        "mac": dev["mac"],
                        "paper_level": round(dev["paper_level"], 1),
                        "battery": round(dev["battery"], 1)
                    })

                if not active_devices:
                    continue

                payload = {
                    "gateway_ip": gw["ip"],
                    "devices": active_devices
                }

                try:
                    resp = client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        print(f"  -> GW {gw['ip']}: OK 200 ({len(active_devices)} devices)")
                    else:
                        print(f"  -> GW {gw['ip']}: Lỗi {resp.status_code} - {resp.text}")
                except Exception as err:
                    print(f"  -> GW {gw['ip']}: Kết nối thất bại: {err}")

            time.sleep(args.interval)

if __name__ == "__main__":
    main()
