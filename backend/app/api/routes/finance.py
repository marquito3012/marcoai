"""
MarcoAI – Finance API Routes (Fase 7)
══════════════════════════════════════════════════════════════════════════════

Endpoints:
  GET  /api/v1/finance/transactions       – Lista transacciones
  POST /api/v1/finance/transactions       – Crea nueva transacción
  GET  /api/v1/finance/transactions/{id}  – Obtiene transacción por ID
  PUT  /api/v1/finance/transactions/{id}  – Actualiza transacción
  DELETE /api/v1/finance/transactions/{id} – Elimina transacción
  GET  /api/v1/finance/balance            – Balance mensual
  GET  /api/v1/finance/summary            – Resumen anual
  GET  /api/v1/finance/categories         – Gastos por categoría
  GET  /api/v1/finance/fixed              – Transacciones fijas/recurrentes
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.db.models import User
from app.services.finance_service import FinanceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finance", tags=["Finanzas"])


# ══════════════════════════════════════════════════════════════════════════════
#  Schemas
# ══════════════════════════════════════════════════════════════════════════════

class TransactionCreate(BaseModel):
    type: Literal["income", "expense"]
    amount: float = Field(..., gt=0, description="Cantidad (siempre positiva)")
    category: str = Field(..., description="Categoría de la transacción")
    description: str = Field(..., min_length=1, max_length=500)
    date: str | None = Field(None, description="Fecha ISO 8601 (default: ahora)")
    is_fixed: bool = Field(False, description="Si es transacción recurrente")
    recurrence: str | None = Field(None, description="Frecuencia: monthly, weekly, etc.")


class TransactionUpdate(BaseModel):
    amount: float | None = None
    category: str | None = None
    description: str | None = None
    date: str | None = None
    is_fixed: bool | None = None
    recurrence: str | None = None


class TransactionResponse(BaseModel):
    id: str
    type: str
    amount: float
    category: str
    description: str
    date: str
    is_fixed: bool
    recurrence: str | None
    created_at: str


class TransactionsListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int


class BalanceResponse(BaseModel):
    month: int
    year: int
    income: float
    expenses: float
    balance: float
    savings_rate: float


class CategorySummary(BaseModel):
    category: str
    total: float
    count: int


class CategoriesSummaryResponse(BaseModel):
    categories: list[CategorySummary]
    total: float


class YearlySummaryResponse(BaseModel):
    year: int
    total_income: float
    total_expenses: float
    total_balance: float
    monthly_breakdown: dict


# ══════════════════════════════════════════════════════════════════════════════
#  Helper
# ══════════════════════════════════════════════════════════════════════════════

async def get_finance_service(user: User, db) -> FinanceService:
    """Obtiene el servicio de finanzas para el usuario actual."""
    return FinanceService(db, user.id)


# ══════════════════════════════════════════════════════════════════════════════
#  Routes
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/transactions", response_model=TransactionsListResponse, summary="Listar transacciones")
async def list_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tx_type: Literal["income", "expense"] | None = None,
    category: str | None = None,
    month: int | None = None,
    year: int | None = None,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """Lista transacciones del usuario con filtros opcionales."""
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_finance_service(current_user, session)

        try:
            transactions = await service.list_transactions(
                limit=limit,
                offset=offset,
                tx_type=tx_type,
                category=category,
                month=month,
                year=year,
            )

            return {
                "transactions": [
                    {
                        "id": tx.id,
                        "type": tx.type,
                        "amount": tx.amount,
                        "category": tx.category,
                        "description": tx.description,
                        "date": tx.date.isoformat(),
                        "is_fixed": tx.is_fixed,
                        "recurrence": tx.recurrence,
                        "created_at": tx.created_at.isoformat(),
                    }
                    for tx in transactions
                ],
                "total": len(transactions),
            }
        except Exception as exc:
            logger.exception("Error listing transactions")
            raise HTTPException(status_code=500, detail="Error al obtener transacciones")


@router.get("/transactions/{tx_id}", response_model=TransactionResponse, summary="Obtener transacción por ID")
async def get_transaction(
    tx_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """Obtiene los detalles de una transacción específica."""
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_finance_service(current_user, session)

        try:
            tx = await service.get_transaction(tx_id)
            if not tx:
                raise HTTPException(status_code=404, detail="Transacción no encontrada")

            return {
                "id": tx.id,
                "type": tx.type,
                "amount": tx.amount,
                "category": tx.category,
                "description": tx.description,
                "date": tx.date.isoformat(),
                "is_fixed": tx.is_fixed,
                "recurrence": tx.recurrence,
                "created_at": tx.created_at.isoformat(),
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error getting transaction")
            raise HTTPException(status_code=500, detail="Error al obtener la transacción")


@router.post("/transactions", response_model=TransactionResponse, status_code=201, summary="Crear transacción")
async def create_transaction(
    body: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """
    Crea una nueva transacción (ingreso o gasto).

    - **type**: "income" o "expense"
    - **amount**: Cantidad (siempre positiva)
    - **category**: Categoría (alimentacion, transporte, ocio, etc.)
    - **description**: Descripción detallada
    - **date**: Fecha opcional (default: ahora)
    - **is_fixed**: Si es transacción fija/recurrente
    - **recurrence**: Frecuencia ("monthly", "weekly")
    """
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_finance_service(current_user, session)

        try:
            date = datetime.fromisoformat(body.date.replace("Z", "+00:00")) if body.date else None

            tx = await service.create_transaction(
                tx_type=body.type,
                amount=body.amount,
                category=body.category,
                description=body.description,
                date=date,
                is_fixed=body.is_fixed,
                recurrence=body.recurrence,
            )

            return {
                "id": tx.id,
                "type": tx.type,
                "amount": tx.amount,
                "category": tx.category,
                "description": tx.description,
                "date": tx.date.isoformat(),
                "is_fixed": tx.is_fixed,
                "recurrence": tx.recurrence,
                "created_at": tx.created_at.isoformat(),
            }
        except Exception as exc:
            logger.exception("Error creating transaction")
            raise HTTPException(status_code=500, detail="Error al crear la transacción")


@router.put("/transactions/{tx_id}", response_model=TransactionResponse, summary="Actualizar transacción")
async def update_transaction(
    tx_id: str,
    body: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """Actualiza una transacción existente."""
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_finance_service(current_user, session)

        try:
            date = datetime.fromisoformat(body.date.replace("Z", "+00:00")) if body.date else None

            tx = await service.update_transaction(
                transaction_id=tx_id,
                amount=body.amount,
                category=body.category,
                description=body.description,
                date=date,
                is_fixed=body.is_fixed,
                recurrence=body.recurrence,
            )

            if not tx:
                raise HTTPException(status_code=404, detail="Transacción no encontrada")

            return {
                "id": tx.id,
                "type": tx.type,
                "amount": tx.amount,
                "category": tx.category,
                "description": tx.description,
                "date": tx.date.isoformat(),
                "is_fixed": tx.is_fixed,
                "recurrence": tx.recurrence,
                "created_at": tx.created_at.isoformat(),
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error updating transaction")
            raise HTTPException(status_code=500, detail="Error al actualizar la transacción")


@router.delete("/transactions/{tx_id}", status_code=204, summary="Eliminar transacción")
async def delete_transaction(
    tx_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """Elimina una transacción."""
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_finance_service(current_user, session)

        try:
            deleted = await service.delete_transaction(tx_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Transacción no encontrada")
            return None
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error deleting transaction")
            raise HTTPException(status_code=500, detail="Error al eliminar la transacción")


@router.get("/balance", response_model=BalanceResponse, summary="Obtener balance mensual")
async def get_balance(
    month: int | None = None,
    year: int | None = None,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """
    Obtiene el balance mensual (ingresos - gastos).

    Si no se especifica, devuelve el balance del mes actual.
    """
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_finance_service(current_user, session)

        try:
            balance = await service.get_monthly_balance(month, year)
            return balance
        except Exception as exc:
            logger.exception("Error getting balance")
            raise HTTPException(status_code=500, detail="Error al obtener el balance")


@router.get("/summary", response_model=YearlySummaryResponse, summary="Resumen anual")
async def get_summary(
    year: int | None = None,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """Obtiene resumen financiero anual completo."""
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_finance_service(current_user, session)

        try:
            summary = await service.get_yearly_summary(year)
            return summary
        except Exception as exc:
            logger.exception("Error getting yearly summary")
            raise HTTPException(status_code=500, detail="Error al obtener el resumen anual")


@router.get("/categories", response_model=CategoriesSummaryResponse, summary="Gastos por categoría")
async def get_categories(
    month: int | None = None,
    year: int | None = None,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """Obtiene gastos desglosados por categoría."""
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_finance_service(current_user, session)

        try:
            categories = await service.get_expenses_by_category(month, year)
            total = sum(c["total"] for c in categories)

            return {
                "categories": categories,
                "total": round(total, 2),
            }
        except Exception as exc:
            logger.exception("Error getting categories")
            raise HTTPException(status_code=500, detail="Error al obtener categorías")


@router.get("/fixed", summary="Transacciones fijas")
async def get_fixed(
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """Obtiene lista de transacciones fijas/recurrentes."""
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_finance_service(current_user, session)

        try:
            transactions = await service.get_fixed_transactions()

            return {
                "transactions": [
                    {
                        "id": tx.id,
                        "type": tx.type,
                        "amount": tx.amount,
                        "category": tx.category,
                        "description": tx.description,
                        "recurrence": tx.recurrence,
                        "date": tx.date.isoformat(),
                    }
                    for tx in transactions
                ],
                "total_expenses": sum(tx.amount for tx in transactions if tx.type == "expense"),
                "total_income": sum(tx.amount for tx in transactions if tx.type == "income"),
            }
        except Exception as exc:
            logger.exception("Error getting fixed transactions")
            raise HTTPException(status_code=500, detail="Error al obtener transacciones fijas")
