import httpx, asyncio
async def main():
    async with httpx.AsyncClient() as c:
        r = await c.get('http://127.0.0.1:5173/admin', timeout=15)
        print(f'Status: {r.status_code}')
        has_not_found = 'Signal lost' in r.text
        print(f'404 page: {has_not_found}')
        print(f'Length: {len(r.text)}')
        has_admin = 'Governance' in r.text or 'Admin' in r.text
        print(f'Has admin content: {has_admin}')
asyncio.run(main())
