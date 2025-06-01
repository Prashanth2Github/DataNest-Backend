from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import pandas as pd
import io
from typing import List, Optional
import zlib
import base64

from database import get_db
import models
from auth import get_current_user, require_admin, get_password_hash, verify_password, create_access_token
from pydantic import BaseModel

router = APIRouter()

# Pydantic models
class UserRegister(BaseModel):
    username: str
    password: str
    role: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserProfile(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

class SalesData(BaseModel):
    customer_name: str
    amount: float
    date: datetime

class AnalyticsSummary(BaseModel):
    total_sales: float
    total_transactions: int
    average_order_value: float

class TopCustomer(BaseModel):
    customer_name: str
    total_sales: float
    transaction_count: int

class StringCompress(BaseModel):
    text: str

class StringCompressResponse(BaseModel):
    original_text: str
    compressed_data: str
    original_size: int
    compressed_size: int
    compression_ratio: float

@router.post("/register")
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    # Validate role
    if user_data.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")
    
    # Check if username already exists
    existing_user = db.query(models.User).filter(models.User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = models.User(
        username=user_data.username,
        password_hash=hashed_password,
        role=user_data.role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User registered successfully", "user_id": new_user.id}

@router.post("/login")
async def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    user = db.query(models.User).filter(models.User.username == user_data.username).first()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }

@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: models.User = Depends(get_current_user)):
    """Get current user profile"""
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        created_at=current_user.created_at
    )

@router.post("/upload-sales")
async def upload_sales_data(
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Upload sales data via CSV (admin only)"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read CSV content
        content = await file.read()
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        # Validate CSV structure
        required_columns = ['customer_name', 'amount', 'date']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=400, 
                detail=f"CSV must contain columns: {', '.join(required_columns)}"
            )
        
        # Process and save data
        sales_records = []
        for _, row in df.iterrows():
            try:
                # Parse date
                date_obj = pd.to_datetime(row['date']).to_pydatetime()
                
                sales_record = models.SalesRecord(
                    customer_name=str(row['customer_name']),
                    amount=float(row['amount']),
                    date=date_obj,
                    uploaded_by=current_user.id
                )
                sales_records.append(sales_record)
            except Exception as e:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error processing row: {str(e)}"
                )
        
        # Save to database
        db.add_all(sales_records)
        db.commit()
        
        return {
            "message": f"Successfully uploaded {len(sales_records)} sales records",
            "records_count": len(sales_records)
        }
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get sales analytics summary (admin only)"""
    # Calculate summary statistics
    summary = db.query(
        func.sum(models.SalesRecord.amount).label('total_sales'),
        func.count(models.SalesRecord.id).label('total_transactions'),
        func.avg(models.SalesRecord.amount).label('average_order_value')
    ).first()
    
    total_sales = summary.total_sales or 0
    total_transactions = summary.total_transactions or 0
    average_order_value = summary.average_order_value or 0
    
    return AnalyticsSummary(
        total_sales=round(total_sales, 2),
        total_transactions=total_transactions,
        average_order_value=round(average_order_value, 2)
    )

@router.get("/analytics/top-customers", response_model=List[TopCustomer])
async def get_top_customers(
    limit: int = Query(3, ge=1, le=100),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get top customers by total sales (admin only)"""
    top_customers = db.query(
        models.SalesRecord.customer_name,
        func.sum(models.SalesRecord.amount).label('total_sales'),
        func.count(models.SalesRecord.id).label('transaction_count')
    ).group_by(
        models.SalesRecord.customer_name
    ).order_by(
        func.sum(models.SalesRecord.amount).desc()
    ).limit(limit).all()
    
    return [
        TopCustomer(
            customer_name=customer.customer_name,
            total_sales=round(customer.total_sales, 2),
            transaction_count=customer.transaction_count
        )
        for customer in top_customers
    ]

@router.get("/analytics/by-date", response_model=List[SalesData])
async def get_sales_by_date(
    from_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get sales data filtered by date range (admin only)"""
    try:
        # Parse dates
        start_date = datetime.strptime(from_date, "%Y-%m-%d")
        end_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
        
        # Query sales records
        sales_records = db.query(models.SalesRecord).filter(
            models.SalesRecord.date >= start_date,
            models.SalesRecord.date < end_date
        ).order_by(models.SalesRecord.date.desc()).all()
        
        return [
            SalesData(
                customer_name=record.customer_name,
                amount=record.amount,
                date=record.date
            )
            for record in sales_records
        ]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@router.post("/compress-string", response_model=StringCompressResponse)
async def compress_string(data: StringCompress):
    """Compress a string using zlib compression"""
    try:
        original_text = data.text
        original_size = len(original_text.encode('utf-8'))
        
        # Compress the string
        compressed_bytes = zlib.compress(original_text.encode('utf-8'))
        compressed_size = len(compressed_bytes)
        
        # Encode to base64 for safe transport
        compressed_data = base64.b64encode(compressed_bytes).decode('utf-8')
        
        # Calculate compression ratio
        compression_ratio = (original_size - compressed_size) / original_size * 100 if original_size > 0 else 0
        
        return StringCompressResponse(
            original_text=original_text,
            compressed_data=compressed_data,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=round(compression_ratio, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Compression failed: {str(e)}")

@router.post("/decompress-string")
async def decompress_string(compressed_data: str):
    """Decompress a base64-encoded compressed string"""
    try:
        # Decode from base64
        compressed_bytes = base64.b64decode(compressed_data)
        
        # Decompress
        decompressed_bytes = zlib.decompress(compressed_bytes)
        decompressed_text = decompressed_bytes.decode('utf-8')
        
        return {
            "decompressed_text": decompressed_text,
            "original_size": len(decompressed_text.encode('utf-8'))
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Decompression failed: {str(e)}")
