from datetime import datetime, date
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, func, update, delete, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    User, Category, Program, Favorite, Rating, AppRequest, MandatoryChannel
)
from app.utils.cache import cache

# ----------------- USERS -----------------
async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    full_name: str,
    username: Optional[str] = None,
    is_admin: bool = False
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        role = "admin" if is_admin else "user"
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=role,
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Update user details if changed
        updated = False
        if user.full_name != full_name:
            user.full_name = full_name
            updated = True
        if user.username != username:
            user.username = username
            updated = True
        if not user.is_active:
            user.is_active = True
            updated = True
        if is_admin and user.role != "admin" and user.role != "owner":
            user.role = "admin"
            updated = True
        if updated:
            await session.commit()
            await session.refresh(user)
    return user

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def increment_user_downloads(session: AsyncSession, user_id: int):
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(downloads_count=User.downloads_count + 1)
    )
    await session.commit()

async def set_user_active_status(session: AsyncSession, telegram_id: int, is_active: bool):
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(is_active=is_active)
    )
    await session.commit()

async def get_all_active_user_ids(session: AsyncSession) -> List[int]:
    result = await session.execute(select(User.telegram_id).where(User.is_active == True))
    return list(result.scalars().all())

# ----------------- CATEGORIES -----------------
DEFAULT_CATEGORIES = [
    ("💻 Windows Dasturlari", "💻", 1),
    ("📱 Android (APK)", "📱", 2),
    ("🍏 macOS", "🍏", 3),
    ("🎨 Grafika & Dizayn", "🎨", 4),
    ("💼 Ofis & Ish yuritish", "💼", 5),
    ("🛡 Antivirus & Xavfsizlik", "🛡", 6),
    ("🛠 Foydali Utilitlar", "🛠", 7),
    ("🎬 Audio & Video tahrirlash", "🎬", 8),
    ("🌐 Internet & Tarmoq dasturlari", "🌐", 9),
]

async def seed_default_categories(session: AsyncSession):
    result = await session.execute(select(func.count(Category.id)))
    count = result.scalar() or 0
    if count == 0:
        for name, icon, order in DEFAULT_CATEGORIES:
            session.add(Category(name=name, icon=icon, order_index=order, is_active=True))
        await session.commit()

async def get_all_categories(session: AsyncSession, active_only: bool = True) -> List[Category]:
    cached = cache.get_cached_categories(active_only)
    if cached is not None:
        return cached

    stmt = select(Category)
    if active_only:
        stmt = stmt.where(Category.is_active == True)
    stmt = stmt.order_by(Category.order_index.asc(), Category.id.asc())
    result = await session.execute(stmt)
    categories = list(result.scalars().all())
    cache.set_cached_categories(categories, active_only)
    return categories

async def get_category_by_id(session: AsyncSession, category_id: int) -> Optional[Category]:
    result = await session.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()

async def create_category(session: AsyncSession, name: str, icon: str = "📁", order_index: int = 0) -> Category:
    cat = Category(name=name, icon=icon, order_index=order_index, is_active=True)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    cache.invalidate_categories()
    return cat

async def delete_category(session: AsyncSession, category_id: int) -> bool:
    cat = await get_category_by_id(session, category_id)
    if cat:
        await session.delete(cat)
        await session.commit()
        cache.invalidate_categories()
        return True
    return False

# ----------------- PROGRAMS -----------------
async def create_program(
    session: AsyncSession,
    title: str,
    category_id: int,
    os_type: str,
    version: str,
    description: str,
    file_id: str,
    file_name: str,
    file_size: int,
    archive_password: Optional[str] = None,
    file_unique_id: Optional[str] = None,
    storage_msg_id: Optional[int] = None,
    image_file_id: Optional[str] = None,
    download_url: Optional[str] = None
) -> Program:
    # Generate unique code like prog_1, prog_2
    temp_code = f"temp_{datetime.utcnow().timestamp()}"
    prog = Program(
        code=temp_code,
        title=title,
        category_id=category_id,
        os_type=os_type.lower(),
        version=version,
        description=description,
        archive_password=archive_password,
        file_id=file_id,
        file_unique_id=file_unique_id,
        storage_msg_id=storage_msg_id,
        file_name=file_name,
        file_size=file_size,
        image_file_id=image_file_id,
        download_url=download_url
    )
    session.add(prog)
    await session.flush()
    prog.code = f"prog_{prog.id}"
    await session.commit()
    await session.refresh(prog)
    return prog

async def get_program_by_id(session: AsyncSession, program_id: int) -> Optional[Program]:
    result = await session.execute(select(Program).where(Program.id == program_id))
    return result.scalar_one_or_none()

async def get_program_by_code(session: AsyncSession, code: str) -> Optional[Program]:
    result = await session.execute(select(Program).where(Program.code == code))
    return result.scalar_one_or_none()

async def get_programs_by_category(
    session: AsyncSession,
    category_id: int,
    limit: int = 5,
    offset: int = 0
) -> Tuple[List[Program], int]:
    count_stmt = select(func.count(Program.id)).where(Program.category_id == category_id)
    total_count = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Program)
        .where(Program.category_id == category_id)
        .order_by(Program.id.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all()), total_count

async def get_programs_by_os(
    session: AsyncSession,
    os_type: str,
    limit: int = 5,
    offset: int = 0
) -> Tuple[List[Program], int]:
    count_stmt = select(func.count(Program.id)).where(Program.os_type == os_type.lower())
    total_count = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Program)
        .where(Program.os_type == os_type.lower())
        .order_by(Program.id.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all()), total_count

async def search_programs(
    session: AsyncSession,
    query: str,
    limit: int = 10,
    offset: int = 0
) -> Tuple[List[Program], int]:
    clean_q = f"%{query.strip()}%"
    filter_condition = or_(
        Program.title.ilike(clean_q),
        Program.description.ilike(clean_q),
        Program.file_name.ilike(clean_q)
    )
    count_stmt = select(func.count(Program.id)).where(filter_condition)
    total_count = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Program)
        .where(filter_condition)
        .order_by(Program.downloads_count.desc(), Program.id.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all()), total_count

async def get_top_programs(session: AsyncSession, limit: int = 10) -> List[Program]:
    stmt = select(Program).order_by(Program.downloads_count.desc(), Program.views_count.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def get_latest_programs(session: AsyncSession, limit: int = 10) -> List[Program]:
    stmt = select(Program).order_by(Program.id.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def increment_views(session: AsyncSession, program_id: int):
    await session.execute(
        update(Program).where(Program.id == program_id).values(views_count=Program.views_count + 1)
    )
    await session.commit()

async def increment_downloads(session: AsyncSession, program_id: int):
    await session.execute(
        update(Program).where(Program.id == program_id).values(downloads_count=Program.downloads_count + 1)
    )
    await session.commit()

async def delete_program(session: AsyncSession, program_id: int) -> bool:
    prog = await get_program_by_id(session, program_id)
    if prog:
        await session.delete(prog)
        await session.commit()
        return True
    return False

async def get_program_rating_stats(session: AsyncSession, program_id: int) -> Tuple[float, int]:
    stmt = select(func.avg(Rating.rating), func.count(Rating.id)).where(Rating.program_id == program_id)
    result = await session.execute(stmt)
    avg_score, count = result.first()
    return float(avg_score or 5.0), int(count or 0)

# ----------------- FAVORITES -----------------
async def toggle_favorite(session: AsyncSession, user_id: int, program_id: int) -> bool:
    """Returns True if added to favorites, False if removed."""
    stmt = select(Favorite).where(Favorite.user_id == user_id, Favorite.program_id == program_id)
    res = await session.execute(stmt)
    fav = res.scalar_one_or_none()
    if fav:
        await session.delete(fav)
        await session.commit()
        return False
    else:
        session.add(Favorite(user_id=user_id, program_id=program_id))
        await session.commit()
        return True

async def is_favorite(session: AsyncSession, user_id: int, program_id: int) -> bool:
    stmt = select(Favorite.id).where(Favorite.user_id == user_id, Favorite.program_id == program_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none() is not None

async def get_user_favorites(
    session: AsyncSession,
    user_id: int,
    limit: int = 5,
    offset: int = 0
) -> Tuple[List[Program], int]:
    count_stmt = select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
    total_count = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Program)
        .join(Favorite, Program.id == Favorite.program_id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.id.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all()), total_count

# ----------------- RATINGS -----------------
async def set_rating(session: AsyncSession, user_id: int, program_id: int, score: int):
    score = max(1, min(5, score))
    stmt = select(Rating).where(Rating.user_id == user_id, Rating.program_id == program_id)
    res = await session.execute(stmt)
    rating_entry = res.scalar_one_or_none()
    if rating_entry:
        rating_entry.rating = score
    else:
        session.add(Rating(user_id=user_id, program_id=program_id, rating=score))
    await session.commit()

# ----------------- APP REQUESTS -----------------
async def create_app_request(
    session: AsyncSession,
    user_id: int,
    telegram_id: int,
    username: Optional[str],
    app_name: str
) -> AppRequest:
    req = AppRequest(
        user_id=user_id,
        telegram_id=telegram_id,
        username=username,
        app_name=app_name,
        status="pending"
    )
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req

async def get_pending_requests(session: AsyncSession, limit: int = 10) -> List[AppRequest]:
    stmt = select(AppRequest).where(AppRequest.status == "pending").order_by(AppRequest.id.desc()).limit(limit)
    res = await session.execute(stmt)
    return list(res.scalars().all())

async def update_request_status(session: AsyncSession, request_id: int, status: str) -> Optional[AppRequest]:
    stmt = select(AppRequest).where(AppRequest.id == request_id)
    res = await session.execute(stmt)
    req = res.scalar_one_or_none()
    if req:
        req.status = status
        await session.commit()
        await session.refresh(req)
    return req

# ----------------- MANDATORY CHANNELS -----------------
async def get_active_channels(session: AsyncSession) -> List[MandatoryChannel]:
    stmt = select(MandatoryChannel).where(MandatoryChannel.is_active == True).order_by(MandatoryChannel.id.asc())
    res = await session.execute(stmt)
    return list(res.scalars().all())

async def add_mandatory_channel(
    session: AsyncSession,
    channel_id: int,
    channel_title: str,
    channel_url: str
) -> MandatoryChannel:
    stmt = select(MandatoryChannel).where(MandatoryChannel.channel_id == channel_id)
    res = await session.execute(stmt)
    chan = res.scalar_one_or_none()
    if chan:
        chan.channel_title = channel_title
        chan.channel_url = channel_url
        chan.is_active = True
    else:
        chan = MandatoryChannel(
            channel_id=channel_id,
            channel_title=channel_title,
            channel_url=channel_url,
            is_active=True
        )
        session.add(chan)
    await session.commit()
    await session.refresh(chan)
    cache.invalidate_channels()
    return chan

async def delete_mandatory_channel(session: AsyncSession, channel_id: int) -> bool:
    stmt = select(MandatoryChannel).where(MandatoryChannel.channel_id == channel_id)
    res = await session.execute(stmt)
    chan = res.scalar_one_or_none()
    if chan:
        await session.delete(chan)
        await session.commit()
        cache.invalidate_channels()
        return True
    return False

# ----------------- STATS -----------------
async def get_full_statistics(session: AsyncSession) -> Dict[str, Any]:
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (await session.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0
    blocked_users = total_users - active_users

    # Today joined
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_users = (await session.execute(select(func.count(User.id)).where(User.joined_at >= today_start))).scalar() or 0

    total_programs = (await session.execute(select(func.count(Program.id)))).scalar() or 0
    win_count = (await session.execute(select(func.count(Program.id)).where(Program.os_type == "windows"))).scalar() or 0
    apk_count = (await session.execute(select(func.count(Program.id)).where(Program.os_type == "android"))).scalar() or 0
    mac_count = (await session.execute(select(func.count(Program.id)).where(Program.os_type == "macos"))).scalar() or 0

    total_downloads = (await session.execute(select(func.sum(Program.downloads_count)))).scalar() or 0
    pending_reqs = (await session.execute(select(func.count(AppRequest.id)).where(AppRequest.status == "pending"))).scalar() or 0

    top_progs = await get_top_programs(session, limit=3)

    return {
        "total_users": total_users,
        "active_users": active_users,
        "blocked_users": blocked_users,
        "today_users": today_users,
        "total_programs": total_programs,
        "win_count": win_count,
        "apk_count": apk_count,
        "mac_count": mac_count,
        "total_downloads": total_downloads,
        "pending_reqs": pending_reqs,
        "top_programs": top_progs
    }
