import asyncio
import psycopg

async def test():
    # Hardcode the connection string exactly as provided by Supabase
    url = "postgresql://postgres.wssmxlqloncdhonzssbj:pMjgepkjLG58xVJl@aws-0-us-east-2.pooler.supabase.com:6543/postgres"
    
    print("Testing with hardcoded connection string...")
    print(f"URL: {url[:50]}...{url[-20:]}")
    
    try:
        conn = await psycopg.AsyncConnection.connect(url)
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT 1')
                result = await cur.fetchone()
                print(f'✅ SUCCESS! Result: {result}')
    except Exception as e:
        print(f'❌ Failed: {e}')
        print(f'Error type: {type(e).__name__}')

asyncio.run(test())