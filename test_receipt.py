import asyncio
import json
import urllib.request
from app.models import Product, Location
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/stocksense_db')
    async with engine.begin() as conn:
        prod = (await conn.execute(select(Product))).scalars().first()
        loc = (await conn.execute(select(Location).where(Location.location_type == 'INTERNAL'))).scalars().first()

    if not prod or not loc:
        print("Missing prod or loc")
        return

    # First login to get token
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/auth/login',
        data=json.dumps({'email': 'aesha.gupta.in@gmail.com', 'password': '12345678'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    res = urllib.request.urlopen(req)
    token = json.loads(res.read())['access_token']

    # Create operation
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    data = {
        'operation_type': 'RECEIPT',
        'partner_name': 'LogiTech',
        'dest_location_id': str(loc.id)
    }
    
    req2 = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/operations/',
        data=json.dumps(data).encode('utf-8'),
        headers=headers
    )
    try:
        res2 = urllib.request.urlopen(req2)
        op_data = json.loads(res2.read())
        op_id = op_data['id']
        print(f"Created op {op_id}")

        # add line
        req3 = urllib.request.Request(
            f'http://127.0.0.1:8000/api/v1/operations/{op_id}/lines',
            data=json.dumps({
                'product_id': str(prod.id),
                'quantity': 100,
                'dest_location_id': str(loc.id)
            }).encode('utf-8'),
            headers=headers
        )
        res3 = urllib.request.urlopen(req3)
        print("Line added")
    except Exception as e:
        print(f"ERROR: {e.read().decode('utf-8')}")

asyncio.run(main())
