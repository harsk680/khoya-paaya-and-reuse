import threading
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.responses import FileResponse
import mimetypes

from sqlalchemy.orm import aliased

from fastapi import UploadFile, File, Form
from pathlib import Path
import shutil
import uuid
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from fastapi.responses import FileResponse
from ai.matching import calculate_match_score

from pydantic import BaseModel
from datetime import datetime

from sqlalchemy.orm import Session
from task_queue import job_queue, add_job_to_queue
from worker import start_worker

from database import SessionLocal
from models import (User, Item, LostReport, FoundReport, Match, Notification, Claim, CommitteeDecision, ReuseListing, Job)

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM
)


app = FastAPI(
    title="Khoya-Paaya & Reuse",
    description="Lost & Found and Reuse Platform",
    version="1.0.0"
)
# Upload directories
UPLOAD_DIR = Path("../uploads")
REUSE_UPLOAD_DIR = UPLOAD_DIR / "reuse"
PRIVATE_FOUND_DIR = UPLOAD_DIR / "private_found"

REUSE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PRIVATE_FOUND_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_image(file: UploadFile, folder: Path):
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are allowed"
        )

    filename = f"{uuid.uuid4().hex}_{Path(file.filename).name}"
    file_path = folder / filename

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if file_path.stat().st_size > 5 * 1024 * 1024:
            file_path.unlink()
            raise HTTPException(
                status_code=400,
                detail="Image size must be less than 5 MB"
            )

        return str(file_path)

    finally:
        file.file.close()
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)
worker_process = None
claim_lock = threading.Lock()


@app.on_event("startup")
def start_background_worker():
    global worker_process

    worker_process = start_worker(job_queue)


@app.on_event("shutdown")
def stop_background_worker():
    global worker_process

    if worker_process is not None:
        worker_process.terminate()
        worker_process.join()

        print("Worker process stopped")

security = HTTPBearer()
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("user_id")

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
@app.get("/api/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user)
):
    return {
        "status": "success",
        "message": "You are authenticated!",
        "user": current_user
    }


# =====
# HOME
# =====

BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIR = BASE_DIR / "frontend"


@app.get("/")
def home():

    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


# ============
# HEALTH CHECK
# ============

@app.get("/api/health")
def health_check():

    return {
        "status": "success",
        "message": "Khoya-Paaya backend is running!"
    }


# ========
# REGISTER
# ========

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "student"
    authority_code: str | None = None


@app.post("/api/register")
@app.post("/api/register")
def register_user(user: UserCreate):

    db: Session = SessionLocal()

    try:
        # Check duplicate email
        existing_user = (
            db.query(User)
            .filter(User.email == user.email)
            .first()
        )

        if existing_user:
            return {
                "status": "error",
                "message": "Email already registered"
            }

        # Validate role
        if user.role not in ["student", "authority"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid user role"
            )

        # Authority registration security
        if user.role == "authority":
            secret_code = os.getenv("AUTHORITY_REGISTRATION_CODE")

            if not secret_code or user.authority_code != secret_code:
                raise HTTPException(
                    status_code=403,
                    detail="Invalid authority registration code"
                )

        # Hash password
        hashed_password = hash_password(user.password)

        # Create user
        new_user = User(
            name=user.name,
            email=user.email,
            password=hashed_password,
            role=user.role
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "status": "success",
            "message": "User registered successfully",
            "user_id": new_user.user_id,
            "role": new_user.role
        }

    finally:
        db.close()

# =========================================================
# LOGIN
# =========================================================
class UserLogin(BaseModel):
    email: str
    password: str


@app.post("/api/login")
def login_user(user: UserLogin):
    db: Session = SessionLocal()

    try:
        existing_user = (
            db.query(User)
            .filter(User.email == user.email)
            .first()
        )

        if not existing_user:
            return {
                "status": "error",
                "message": "Invalid email or password"
            }

        password_correct = verify_password(
            user.password,
            existing_user.password
        )

        if not password_correct:
            return {
                "status": "error",
                "message": "Invalid email or password"
            }

        # Create JWT token
        token = create_access_token({
            "user_id": existing_user.user_id,
            "email": existing_user.email,
            "role": existing_user.role
        })

        return {
            "status": "success",
            "message": "Login successful",
            "access_token": token,
            "user_id": existing_user.user_id,
            "name": existing_user.name,
            "role": existing_user.role
        }

    finally:
        db.close()

# CHANGE PASSWORD

class ChangePassword(BaseModel):
    old_password: str
    new_password: str


@app.post("/api/change-password")
def change_password(
    data: ChangePassword,
    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        user = db.query(User).filter(
            User.user_id == current_user["user_id"]
        ).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # Verify old password
        if not verify_password(data.old_password, user.password):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect"
            )

        # Validate new password
        if len(data.new_password) < 8:
            raise HTTPException(
                status_code=400,
                detail="New password must be at least 8 characters"
            )

        if data.old_password == data.new_password:
            raise HTTPException(
                status_code=400,
                detail="New password must be different"
            )

        # Hash and update password
        user.password = hash_password(data.new_password)

        db.commit()

        return {
            "status": "success",
            "message": "Password changed successfully"
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to change password"
        )

    finally:
        db.close()



        # LOST ITEM

class LostItemCreate(BaseModel):
    title: str
    description: str
    category: str
    location: str
    lost_date: datetime
@app.post("/api/lost")
def report_lost_item(
    item: LostItemCreate,
    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        # 1. Create item
        new_item = Item(
            title=item.title,
            description=item.description,
            category=item.category,
            location=item.location,
            item_date=item.lost_date,
            status="lost"
        )

        db.add(new_item)
        db.flush()

        # 2. Create lost report
        new_lost_report = LostReport(
            item_id=new_item.item_id,
            user_id=current_user["user_id"],
            lost_date=item.lost_date,
            lost_location=item.location
        )

        db.add(new_lost_report)

        # 3. Save both changes
        db.commit()
        db.refresh(new_lost_report)

        return {
            "status": "success",
            "message": "Lost item reported successfully",
            "lost_id": new_lost_report.lost_id,
            "item_id": new_item.item_id
        }

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()
        # FOUND ITEM

class FoundItemCreate(BaseModel):
    title: str
    description: str
    category: str
    location: str
    found_date: datetime
class ClaimCreate(BaseModel):
        found_id: int
class CommitteeDecisionCreate(BaseModel):
    claim_id: int
    decision: str
    remarks: str


@app.post("/api/committee-decision")
def create_committee_decision(
    decision: CommitteeDecisionCreate,
    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        # Only admin or authority can decide
        if current_user.get("role") not in ["admin", "authority"]:
            raise HTTPException(
                status_code=403,
                detail="Only admin or authority can make committee decisions"
            )

        # Validate decision
        decision_status = decision.decision.lower().strip()

        if decision_status not in ["approved", "rejected"]:
            raise HTTPException(
                status_code=400,
                detail="Decision must be approved or rejected"
            )

        # Find claim
        claim = (
            db.query(Claim)
            .filter(Claim.claim_id == decision.claim_id)
            .first()
        )

        if not claim:
            raise HTTPException(
                status_code=404,
                detail="Claim not found"
            )

        # Prevent repeated decisions
        if claim.status != "pending":
            raise HTTPException(
                status_code=400,
                detail="This claim has already been decided"
            )

        # Find found report
        found_report = (
            db.query(FoundReport)
            .filter(FoundReport.found_id == claim.found_id)
            .first()
        )

        if not found_report:
            raise HTTPException(
                status_code=404,
                detail="Found report not found"
            )

        # Record committee decision
        new_decision = CommitteeDecision(
            claim_id=claim.claim_id,
            decided_by=current_user["user_id"],
            decision=decision_status,
            remarks=decision.remarks
        )

        db.add(new_decision)

        # Update selected claim
        claim.status = decision_status

        if decision_status == "approved":

            # Reject other pending claims for this item
            (
                db.query(Claim)
                .filter(
                    Claim.found_id == claim.found_id,
                    Claim.claim_id != claim.claim_id,
                    Claim.status == "pending"
                )
                .update(
                    {"status": "rejected"},
                    synchronize_session=False
                )
            )

            # Mark item as returned
            item = (
                db.query(Item)
                .filter(Item.item_id == found_report.item_id)
                .first()
            )

            if not item:
                raise HTTPException(
                    status_code=404,
                    detail="Item not found"
                )

            item.status = "returned"

        db.commit()
        db.refresh(new_decision)

        return {
            "status": "success",
            "message": "Committee decision recorded successfully",
            "decision_id": new_decision.decision_id,
            "claim_id": claim.claim_id,
            "decision": decision_status
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()

@app.get("/api/authority/claim-history")
def get_claim_history(
    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        if current_user.get("role") not in ["admin", "authority"]:
            raise HTTPException(
                status_code=403,
                detail="Only authority can view claim history"
            )

        history = (
            db.query(
                CommitteeDecision.decision_id,
                CommitteeDecision.claim_id,
                CommitteeDecision.decision,
                CommitteeDecision.remarks,
                CommitteeDecision.decided_at,
                Claim.found_id,
                User.name.label("decided_by_name")
            )
            .join(
                Claim,
                CommitteeDecision.claim_id == Claim.claim_id
            )
            .join(
                User,
                CommitteeDecision.decided_by == User.user_id
            )
            .order_by(CommitteeDecision.decided_at.desc())
            .all()
        )

        return {
            "status": "success",
            "total": len(history),
            "history": [
                {
                    "decision_id": row.decision_id,
                    "claim_id": row.claim_id,
                    "found_id": row.found_id,
                    "decision": row.decision,
                    "remarks": row.remarks,
                    "decided_at": row.decided_at,
                    "decided_by": row.decided_by_name
                }
                for row in history
            ]
        }

    finally:
        db.close()

# REUSE

class ReuseListingCreate(BaseModel):
    title: str
    description: str
    category: str
    price: float = 0
    condition_status: str
@app.post("/api/reuse")
def create_reuse_listing(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    price: float = Form(0),
    condition_status: str = Form(...),
    image: UploadFile | None = File(None),
    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        # 1. Save reuse image if provided
        image_path = None

        if image and image.filename:
            image_path = save_uploaded_image(
                image,
                REUSE_UPLOAD_DIR
            )

        # 2. Create reuse listing
        new_listing = ReuseListing(
            user_id=current_user["user_id"],
            title=title,
            description=description,
            category=category,
            price=price,
            condition_status=condition_status,
            image_path=image_path,
            status="available"
        )

        db.add(new_listing)
        db.commit()
        db.refresh(new_listing)

        return {
            "status": "success",
            "message": "Reuse listing created successfully",
            "listing_id": new_listing.listing_id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
@app.get("/api/reuse")
def get_reuse_listings():
    db: Session = SessionLocal()

    try:
        listings = (
            db.query(ReuseListing)
            .filter(ReuseListing.status == "available")
            .order_by(ReuseListing.created_at.desc())
            .all()
        )

        return {
            "status": "success",
            "total": len(listings),
            "listings": [
                {
                    "listing_id": listing.listing_id,
                    "user_id": listing.user_id,
                    "title": listing.title,
                    "description": listing.description,
                    "category": listing.category,
                    "price": float(listing.price or 0),
                    "condition_status": listing.condition_status,
                    "image_available": bool(listing.image_path),
                    "status": listing.status
                }
                for listing in listings
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()

@app.get("/api/reuse/{listing_id}/image")
def get_reuse_image(listing_id: int):
    db: Session = SessionLocal()

    try:
        listing = db.query(ReuseListing).filter(
            ReuseListing.listing_id == listing_id,
            ReuseListing.status == "available"
        ).first()

        if not listing:
            raise HTTPException(
                status_code=404,
                detail="Reuse listing not found"
            )

        if not listing.image_path:
            raise HTTPException(
                status_code=404,
                detail="Image not available"
            )

        image_path = Path(listing.image_path).resolve()
        reuse_folder = REUSE_UPLOAD_DIR.resolve()

        if not image_path.is_relative_to(reuse_folder):
            raise HTTPException(
                status_code=403,
                detail="Invalid image path"
            )

        if not image_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="Image file not found"
            )

        return FileResponse(
            path=str(image_path),
            media_type=mimetypes.guess_type(str(image_path))[0]
            or "application/octet-stream"
        )

    finally:
        db.close()


@app.get("/api/reuse/{listing_id}/seller")
def get_reuse_seller(
    listing_id: int,
    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        listing = db.query(ReuseListing).filter(
            ReuseListing.listing_id == listing_id,
            ReuseListing.status == "available"
        ).first()

        if not listing:
            raise HTTPException(
                status_code=404,
                detail="Listing not found"
            )

        # Prevent seller from contacting themselves
        if listing.user_id == current_user["user_id"]:
            raise HTTPException(
                status_code=403,
                detail="This is your own listing"
            )

        seller = db.query(User).filter(
            User.user_id == listing.user_id
        ).first()

        if not seller:
            raise HTTPException(
                status_code=404,
                detail="Seller not found"
            )

        return {
            "status": "success",
            "seller": {
                "name": seller.name,
                "email": seller.email
            }
        }

    finally:
        db.close()

@app.delete("/api/reuse/{listing_id}")
def delete_reuse_listing(
    listing_id: int,
    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        listing = db.query(ReuseListing).filter(
            ReuseListing.listing_id == listing_id
        ).first()

        if not listing:
            raise HTTPException(
                status_code=404,
                detail="Listing not found"
            )

        # Only listing owner can delete
        if listing.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own listing"
            )

        # Delete associated image safely
        if listing.image_path:
            image_path = Path(listing.image_path).resolve()
            reuse_folder = REUSE_UPLOAD_DIR.resolve()

            if image_path.is_relative_to(reuse_folder):
                if image_path.is_file():
                    image_path.unlink()

        db.delete(listing)
        db.commit()

        return {
            "status": "success",
            "message": "Reuse listing deleted successfully"
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@app.post("/api/claim")
def create_claim(
    claim: ClaimCreate,
    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        # Synchronize simultaneous claim requests
        with claim_lock:

            # Lock the found report row in MySQL
            found_report = (
                db.query(FoundReport)
                .filter(
                    FoundReport.found_id == claim.found_id
                )
                .with_for_update()
                .first()
            )

            if not found_report:
                raise HTTPException(
                    status_code=404,
                    detail="Found report not found"
                )

            # Prevent finder from claiming their own found item
            if found_report.user_id == current_user["user_id"]:
                raise HTTPException(
                    status_code=403,
                    detail="You cannot claim an item reported by yourself"
                    )
            # Get the found item's category
            found_item = db.query(Item).filter(
                Item.item_id == found_report.item_id
                ).first()
            # Check whether claimant reported losing an item from the same category
            matching_lost_report = (
                db.query(LostReport)
                .join(Item, LostReport.item_id == Item.item_id)
                .filter(
                    LostReport.user_id == current_user["user_id"],
                    Item.category == found_item.category
                    )
                    .first()
                    )
            if not matching_lost_report:
                raise HTTPException(
                    status_code=403,
                    detail="You must have a lost report in the same category to claim this item"
                    )

            
            # Prevent duplicate claims by the same user 
            existing_claim = (
                db.query(Claim)
                .filter(
                    Claim.found_id == claim.found_id,
                    Claim.claimant_id == current_user["user_id"]
                    )
                    .first()
                    )
            if existing_claim:
                raise HTTPException(
                    status_code=400,
                    detail="You have already submitted a claim for this item"
                    )

            # Create a pending claim
            new_claim = Claim(
                found_id=claim.found_id,
                claimant_id=current_user["user_id"],
                status="pending"
            )

            db.add(new_claim)

            # Commit releases the database row lock
            db.commit()
            db.refresh(new_claim)

            return {
                "status": "success",
                "message": "Claim submitted successfully",
                "claim_id": new_claim.claim_id,
                "found_id": new_claim.found_id,
                "claimant_id": new_claim.claimant_id,
                "claim_status": new_claim.status
            }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()

@app.get("/api/authority/pending-claims")
def get_pending_claims(
    current_user: dict = Depends(get_current_user)
):
    # Only authority can view claims
    if current_user["role"] != "authority":
        raise HTTPException(
            status_code=403,
            detail="Only authority can view pending claims"
        )

    db = SessionLocal()

    try:
        claims = (
            db.query(Claim, FoundReport, Item, User)
            .join(
                FoundReport,
                Claim.found_id == FoundReport.found_id
            )
            .join(
                Item,
                FoundReport.item_id == Item.item_id
            )
            .join(
                User,
                Claim.claimant_id == User.user_id
            )
            .filter(Claim.status == "pending")
            .order_by(Claim.claim_date.asc())
            .all()
        )

        return {
            "status": "success",
            "total": len(claims),
            "claims": [
                {
                    "claim_id": claim.claim_id,
                    "found_id": found.found_id,
                    "category": item.category,
                    "title": item.title,
                    "claimant_id": claimant.user_id,
                    "claimant_name": claimant.name,
                    "claimant_email": claimant.email,
                    "claim_date": (
                        claim.claim_date.strftime("%Y-%m-%d %H:%M")
                        if claim.claim_date else None
                    )
                }
                for claim, found, item, claimant in claims
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@app.get("/api/authority/possible-matches")
def get_possible_matches(
    current_user: dict = Depends(get_current_user)
):
    # Only authority can view AI match scores
    if current_user["role"] != "authority":
        raise HTTPException(
            status_code=403,
            detail="Only authority can view possible matches"
        )

    db = SessionLocal()

    try:
        LostItem = aliased(Item)
        FoundItem = aliased(Item)

        matches = (
            db.query(
                Match,
                LostReport,
                FoundReport,
                LostItem,
                FoundItem
            )
            .join(
                LostReport,
                Match.lost_id == LostReport.lost_id
            )
            .join(
                FoundReport,
                Match.found_id == FoundReport.found_id
            )
            .join(
                LostItem,
                LostReport.item_id == LostItem.item_id
            )
            .join(
                FoundItem,
                FoundReport.item_id == FoundItem.item_id
            )
            .filter(Match.match_score >= 50)
            .order_by(Match.match_score.desc())
            .all()
        )

        return {
            "status": "success",
            "total": len(matches),
            "matches": [
                {
                    "match_id": match.match_id,
                    "lost_id": lost.lost_id,
                    "found_id": found.found_id,

                    "lost_title": lost_item.title,
                    "found_title": found_item.title,

                    "lost_category": lost_item.category,
                    "found_category": found_item.category,

                    "lost_location": lost.lost_location,
                    "found_location": found.found_location,

                    "match_score": float(match.match_score),
                    "match_status": match.status,

                    "created_at": (
                        match.created_at.strftime("%Y-%m-%d %H:%M")
                        if match.created_at else None
                    )
                }
                for match, lost, found, lost_item, found_item in matches
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()


def create_job(
    db: Session,
    job_type: str,
    reference_id: int,
    priority: int = 3,
    found_reference_id: int = None
):
    new_job = Job(
        job_type=job_type,
        reference_id=reference_id,
        found_reference_id=found_reference_id,
        priority=priority,
        status="waiting"
    )

    db.add(new_job)
    db.flush()

    return new_job

@app.post("/api/os/test-job")
def test_os_job(

    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        job = create_job(
            db=db,
            job_type="TEST",
            reference_id=current_user["user_id"],
            priority=2
        )

        db.commit()
        # Add job to queue only after successful database commit
        add_job_to_queue(job.job_id)
        return {
    "status": "success",
    "message": "OS job added to queue",
    "job_id": job.job_id,
    "job_status": job.status
}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()

@app.post("/api/os/test-priority")
def test_priority_scheduling(
    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        priorities = [3, 1, 2, 1]
        jobs = []

        # Create all jobs first
        for priority in priorities:
            job = create_job(
                db=db,
                job_type="TEST",
                reference_id=current_user["user_id"],
                priority=priority
            )
            jobs.append(job)

        # Save all jobs before notifying worker
        db.commit()

        job_ids = [job.job_id for job in jobs]

        # Send one queue signal per committed job
        for job_id in job_ids:
            add_job_to_queue(job_id)

        return {
            "status": "success",
            "message": "Priority test jobs added",
            "job_ids": job_ids,
            "priorities": priorities
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()

@app.post("/api/found")
def report_found_item(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    found_date: datetime = Form(...),
    verification_image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        # 1. Save private verification image
        image_path = save_uploaded_image(
            verification_image,
            PRIVATE_FOUND_DIR
        )

        # 2. Create item
        new_item = Item(
            title=title,
            description=description,
            category=category,
            location=location,
            item_date=found_date,
            status="found"
        )

        db.add(new_item)
        db.flush()

        # 3. Create found report
        new_found_report = FoundReport(
            item_id=new_item.item_id,
            user_id=current_user["user_id"],
            found_date=found_date,
            found_location=location,
            verification_image_path=image_path
        )

        db.add(new_found_report)

        # Find students who reported losing an item in the same category
        lost_users = (
            db.query(LostReport.user_id)
            .join(Item, LostReport.item_id == Item.item_id)
            .filter(
                Item.category == category,
                LostReport.user_id != current_user["user_id"]
                )
                .distinct()
                .all()
                )
        # Create an in-app notification for each matching student
        for (lost_user_id,) in lost_users:
            notification = Notification(
                user_id=lost_user_id,
                message=f"A possible {category} item has been found. Check the Found Items section."
                )
            db.add(notification)
            db.commit()
            db.refresh(new_found_report)

        return {
            "status": "success",
            "message": "Found item reported successfully",
            "found_id": new_found_report.found_id,
            "item_id": new_item.item_id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()

@app.get("/api/found")
def get_public_found_items():
    db: Session = SessionLocal()

    try:
        found_items = (
            db.query(FoundReport, Item)
            .join(Item, FoundReport.item_id == Item.item_id)
            .filter(Item.status == "found")
            .order_by(FoundReport.created_at.desc())
            .all()
        )

        return {
            "status": "success",
            "total": len(found_items),
            "found_items": [
                {
                    "found_id": report.found_id,
                    "category": item.category,
                    "found_date": report.found_date.strftime("%Y-%m-%d")
                }
                for report, item in found_items
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@app.post("/api/match/{lost_id}/{found_id}")
def create_match(
    lost_id: int,
    found_id: int,
    current_user: dict = Depends(get_current_user)
):
    db: Session = SessionLocal()

    try:
        # Check lost report
        lost_report = (
            db.query(LostReport)
            .filter(LostReport.lost_id == lost_id)
            .first()
        )

        if not lost_report:
            raise HTTPException(
                status_code=404,
                detail="Lost report not found"
            )

        # Check found report
        found_report = (
            db.query(FoundReport)
            .filter(FoundReport.found_id == found_id)
            .first()
        )

        if not found_report:
            raise HTTPException(
                status_code=404,
                detail="Found report not found"
            )

        # Create background AI matching job
        job = create_job(
            db=db,
            job_type="AI_MATCH",
            reference_id=lost_id,
            priority=2,
            found_reference_id=found_id
        )

        # Commit before notifying worker
        db.commit()

        # Send job signal to multiprocessing queue
        add_job_to_queue(job.job_id)

        return {
            "status": "success",
            "message": "AI matching job added to background queue",
            "job_id": job.job_id,
            "lost_id": lost_id,
            "found_id": found_id,
            "job_status": "waiting"
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()

@app.get("/api/authority/found/{found_id}/verification-image")
def get_verification_image(
    found_id: int,
    current_user: dict = Depends(get_current_user)
):
    # Only authority/admin can access
    if current_user.get("role") not in ["authority", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Authority only."
        )

    db: Session = SessionLocal()

    try:
        found_report = db.query(FoundReport).filter(
            FoundReport.found_id == found_id
        ).first()

        if not found_report:
            raise HTTPException(
                status_code=404,
                detail="Found report not found"
            )

        if not found_report.verification_image_path:
            raise HTTPException(
                status_code=404,
                detail="Verification image not available"
            )

        # Ensure file stays inside private folder
        private_folder = PRIVATE_FOUND_DIR.resolve()
        image_path = Path(
            found_report.verification_image_path
        ).resolve()

        if not image_path.is_relative_to(private_folder):
            raise HTTPException(
                status_code=403,
                detail="Invalid image path"
            )

        if not image_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="Image file not found"
            )

        media_type, _ = mimetypes.guess_type(str(image_path))

        return FileResponse(
            path=str(image_path),
            media_type=media_type or "application/octet-stream",
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff"
            }
        )

    finally:
        db.close()
