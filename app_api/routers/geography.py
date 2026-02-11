from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
import asyncpg

from database import get_pool
from models.geography import (
    Country, State, County, CountrySyncUpdate,
    StateSyncUpdate, CountySyncUpdate
)

router = APIRouter()


# Countries endpoints
@router.get("/countries", response_model=List[Country])
async def list_countries(
    sync_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """List countries."""
    query = "SELECT * FROM bcfy_countries WHERE 1=1"
    params = []
    param_count = 1

    if sync_only:
        query += " AND sync = TRUE"

    query += f" ORDER BY country_name LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [dict(row) for row in rows]


@router.get("/countries/{coid}", response_model=Country)
async def get_country(
    coid: int,
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get a specific country."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM bcfy_countries WHERE coid = $1",
            coid
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Country not found")

    return dict(row)


@router.patch("/countries/{coid}", response_model=Country)
async def update_country(
    coid: int,
    payload: CountrySyncUpdate,
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Update country sync status."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE bcfy_countries SET sync = $1 WHERE coid = $2 RETURNING *",
            payload.sync,
            coid
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Country not found")

    return dict(row)


# States endpoints
@router.get("/states", response_model=List[State])
async def list_states(
    coid: Optional[int] = Query(None),
    sync_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """List states."""
    query = "SELECT * FROM bcfy_states WHERE 1=1"
    params = []
    param_count = 1

    if coid is not None:
        query += f" AND coid = ${param_count}"
        params.append(coid)
        param_count += 1

    if sync_only:
        query += " AND sync = TRUE"

    query += f" ORDER BY state_name LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [dict(row) for row in rows]


@router.get("/states/{stid}", response_model=State)
async def get_state(
    stid: int,
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get a specific state."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM bcfy_states WHERE stid = $1",
            stid
        )

    if row is None:
        raise HTTPException(status_code=404, detail="State not found")

    return dict(row)


@router.patch("/states/{stid}", response_model=State)
async def update_state(
    stid: int,
    payload: StateSyncUpdate,
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Update state sync status."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE bcfy_states SET sync = $1 WHERE stid = $2 RETURNING *",
            payload.sync,
            stid
        )

    if row is None:
        raise HTTPException(status_code=404, detail="State not found")

    return dict(row)


# Counties endpoints
@router.get("/counties", response_model=List[County])
async def list_counties(
    stid: Optional[int] = Query(None),
    sync_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """List counties."""
    query = "SELECT * FROM bcfy_counties WHERE 1=1"
    params = []
    param_count = 1

    if stid is not None:
        query += f" AND stid = ${param_count}"
        params.append(stid)
        param_count += 1

    if sync_only:
        query += " AND sync = TRUE"

    query += f" ORDER BY county_name LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [dict(row) for row in rows]


@router.get("/counties/{cntid}", response_model=County)
async def get_county(
    cntid: int,
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get a specific county."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM bcfy_counties WHERE cntid = $1",
            cntid
        )

    if row is None:
        raise HTTPException(status_code=404, detail="County not found")

    return dict(row)


@router.patch("/counties/{cntid}", response_model=County)
async def update_county(
    cntid: int,
    payload: CountySyncUpdate,
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Update county sync status."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE bcfy_counties SET sync = $1 WHERE cntid = $2 RETURNING *",
            payload.sync,
            cntid
        )

    if row is None:
        raise HTTPException(status_code=404, detail="County not found")

    return dict(row)
