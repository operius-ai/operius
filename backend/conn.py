""" Connect to Postgres DB """

import asyncpg
import asyncio
from pgvector.asyncpg import register_vector

async def connect_to_postgres():
    # Connection string from Terraform output
    conn_string = "postgresql://pgadmin:password@server.postgres.database.azure.com:5432/db?sslmode=require"
    
    conn = await asyncpg.connect(conn_string)
    await register_vector(conn)
    
    # Test query
    result = await conn.fetch("SELECT version();")
    print(result)
    
    await conn.close()

# Run
asyncio.run(connect_to_postgres())