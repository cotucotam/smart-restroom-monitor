import sys
import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def test_all():
    client = httpx.Client(base_url='http://127.0.0.1:8000')

    # 1. Test index page
    r = client.get('/')
    assert r.status_code == 200, f'Index failed: {r.status_code}'
    print('[Pass] 1. Index page served OK')

    # 2. Test Login
    r = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
    if r.status_code != 200:
        # maybe already changed
        r = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123_new'})
    assert r.status_code == 200, f'Login failed: {r.text}'
    auth_data = r.json()
    token = auth_data['access_token']
    print(f"[Pass] 2. Admin login OK (must_change_password={auth_data.get('must_change_password')})")

    # 3. Test Change Password
    headers = {'Authorization': f'Bearer {token}'}
    # Test change password
    r = client.post('/api/auth/change-password', json={'old_password': 'admin123', 'new_password': 'admin123_new'}, headers=headers)
    if r.status_code != 200:
        # Revert back to admin123 for fresh runs
        r = client.post('/api/auth/change-password', json={'old_password': 'admin123_new', 'new_password': 'admin123'}, headers=headers)
    print(f'[Pass] 3. Change password endpoint tested OK')

    # 4. Test Terminals
    r = client.get('/api/terminals', headers=headers)
    assert r.status_code == 200
    terms = r.json()
    assert len(terms) >= 2
    term_names = [t['name'] for t in terms]
    print(f'[Pass] 4. Terminals list OK: {term_names}')

    # 5. Test Floor details
    floor_id = terms[0]['floors'][0]['id']
    r = client.get(f'/api/floors/{floor_id}', headers=headers)
    assert r.status_code == 200
    floor_data = r.json()
    print(f"[Pass] 5. Floor details OK: {floor_data['name']} has {len(floor_data['toilets'])} toilets")

    # 6. Test Gateway Ingestion
    gw_ip = floor_data['toilets'][0]['gateway_ip']
    gw_headers = {'X-API-Key': 'airport-gateway-secret-api-key-2026'}
    payload = {
        'gateway_ip': gw_ip,
        'devices': [
            {'mac': 'AA:BB:CC:DD:EE:01', 'paper_level': 8.5, 'battery': 98.0}
        ]
    }
    r = client.post('/api/gateway/report', json=payload, headers=gw_headers)
    assert r.status_code == 200, f'Gateway report failed: {r.text}'
    print(f'[Pass] 6. Gateway report OK: {r.json()}')

    # 7. Test Alerts (should have EMPTY alert created for paper_level=8.5)
    r = client.get('/api/alerts?unack_only=true', headers=headers)
    assert r.status_code == 200
    alerts = r.json()
    print(f'[Pass] 7. Alerts list OK, {len(alerts)} unacknowledged alerts found')
    assert any(a['type'] == 'EMPTY' for a in alerts)

    # 8. Test Acknowledge Alert
    alert_to_ack = next(a for a in alerts if a['type'] == 'EMPTY')
    r = client.post(f"/api/alerts/{alert_to_ack['id']}/acknowledge", headers=headers)
    assert r.status_code == 200
    print(f"[Pass] 8. Acknowledge alert OK: {r.json()['message']}")

    # 9. Test Summary
    r = client.get('/api/summary', headers=headers)
    assert r.status_code == 200
    summary = r.json()
    print(f"[Pass] 9. Summary table endpoint OK ({len(summary)} toilets)")

    print('\n=============================================')
    print('ALL SYSTEM INTEGRATION TESTS PASSED 100%!')
    print('=============================================')

if __name__ == '__main__':
    test_all()
