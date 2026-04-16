"""
MarcoAI – Finance Service (Fase 7)
══════════════════════════════════════════════════════════════════════════════

Servicio para gestionar transacciones financieras (ingresos/gastos).

Características:
  - CRUD de transacciones
  - Cálculo de balances mensuales
  - Agregación por categoría
  - Soporte para transacciones fijas/recurrentes
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
import calendar

from app.db.models import Transaction

logger = logging.getLogger(__name__)

# Categorías predefinidas para clasificación automática
CATEGORIES_EXPENSE = [
    "alimentacion",
    "transporte",
    "ocio",
    "tecnologia",
    "salud",
    "hogar",
    "servicios",
    "compras",
    "otros",
]

CATEGORIES_INCOME = [
    "salario",
    "freelance",
    "inversiones",
    "regalo",
    "otros",
]


class FinanceService:
    """
    Servicio de finanzas para gestión de transacciones.

    Uso:
        service = FinanceService(db, user_id)
        tx = await service.create_transaction(...)
        balance = await service.get_monthly_balance()
    """

    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id

    # ══════════════════════════════════════════════════════════════════════════
    #  CRUD Operations
    # ══════════════════════════════════════════════════════════════════════════

    async def create_transaction(
        self,
        tx_type: str,
        amount: float,
        category: str,
        description: str,
        date: datetime | None = None,
        is_fixed: bool = False,
        recurrence: str | None = None,
    ) -> Transaction:
        """
        Crea una nueva transacción.

        Args:
            tx_type: "income" o "expense"
            amount: Cantidad (siempre positiva)
            category: Categoría de la transacción
            description: Descripción detallada
            date: Fecha de la transacción (default: ahora)
            is_fixed: Si es una transacción recurrente/fija
            recurrence: Frecuencia ("monthly", "weekly", etc.)
        """
        transaction = Transaction(
            user_id=self.user_id,
            type=tx_type,
            amount=amount,
            category=category,
            description=description,
            date=date or datetime.now(timezone.utc),
            is_fixed=is_fixed,
            recurrence=recurrence,
        )

        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)

        logger.info(
            "Transacción creada: %s %s€ (%s) para user=%s",
            tx_type, amount, category, self.user_id
        )

        return transaction

    async def get_transaction(self, transaction_id: str) -> Transaction | None:
        """Obtiene una transacción por su ID."""
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == self.user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_transactions(
        self,
        limit: int = 50,
        offset: int = 0,
        tx_type: str | None = None,
        category: str | None = None,
        month: int | None = None,
        year: int | None = None,
    ) -> list[Transaction]:
        """
        Lista transacciones del usuario con filtros opcionales.

        Args:
            limit: Máximo número de resultados
            offset: Desplazamiento para paginación
            tx_type: Filtrar por tipo ("income" o "expense")
            category: Filtrar por categoría
            month: Filtrar por mes (1-12)
            year: Filtrar por año
        """
        query = select(Transaction).where(Transaction.user_id == self.user_id)

        if tx_type:
            query = query.where(Transaction.type == tx_type)
        if category:
            query = query.where(Transaction.category == category)
        
        if month and year:
            # logic for specific month/year
            month_start = datetime(year, month, 1, tzinfo=timezone.utc)
            _, last_day = calendar.monthrange(year, month)
            month_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

            # Condition:
            # 1. Non-fixed: must be in this month
            # 2. Fixed: must have started before or during this month AND not deleted before this month
            query = query.where(
                or_(
                    and_(
                        Transaction.is_fixed == False,
                        Transaction.date >= month_start,
                        Transaction.date <= month_end
                    ),
                    and_(
                        Transaction.is_fixed == True,
                        Transaction.date <= month_end,
                        or_(
                            Transaction.deleted_at == None,
                            Transaction.deleted_at >= month_start
                        )
                    )
                )
            )
        elif year:
            query = query.where(func.strftime("%Y", Transaction.date) == str(year))
        elif month:
            query = query.where(func.strftime("%m", Transaction.date) == f"{month:02d}")

        query = query.order_by(Transaction.date.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_transaction(
        self,
        transaction_id: str,
        amount: float | None = None,
        category: str | None = None,
        description: str | None = None,
        date: datetime | None = None,
        is_fixed: bool | None = None,
        recurrence: str | None = None,
    ) -> Transaction | None:
        """Actualiza una transacción existente."""
        transaction = await self.get_transaction(transaction_id)
        if not transaction:
            return None

        if amount is not None:
            transaction.amount = amount
        if category is not None:
            transaction.category = category
        if description is not None:
            transaction.description = description
        if date is not None:
            transaction.date = date
        if is_fixed is not None:
            transaction.is_fixed = is_fixed
        if recurrence is not None:
            transaction.recurrence = recurrence

        await self.db.commit()
        await self.db.refresh(transaction)

        return transaction

    async def delete_transaction(self, transaction_id: str) -> bool:
        """Elimina una transacción (soft-delete si es fija)."""
        transaction = await self.get_transaction(transaction_id)
        if not transaction:
            return False

        if transaction.is_fixed:
            # Si es fija, solo marcamos fecha de fin (soft-delete)
            transaction.deleted_at = datetime.now(timezone.utc)
            await self.db.commit()
            logger.info("Transacción fija desactivada (soft-delete): %s", transaction_id)
        else:
            # Si es puntual, borrado físico (o también soft-delete, pero el usuario pidió que desaparezca)
            await self.db.delete(transaction)
            await self.db.commit()
            logger.info("Transacción puntual eliminada físicamente: %s", transaction_id)
            
        return True

    # ══════════════════════════════════════════════════════════════════════════
    #  Balance & Aggregations
    # ══════════════════════════════════════════════════════════════════════════

    async def get_monthly_balance(
        self,
        month: int | None = None,
        year: int | None = None,
    ) -> dict[str, float]:
        """
        Calcula el balance mensual (ingresos - gastos).

        Returns:
            Dict con:
                - income: Total de ingresos
                - expenses: Total de gastos
                - balance: Balance neto
                - savings_rate: Porcentaje de ahorro (si aplica)
        """
        now = datetime.now(timezone.utc)
        month = month or now.month
        year = year or now.year

        # logic for specific month/year
        month_start = datetime(year, month, 1, tzinfo=timezone.utc)
        _, last_day = calendar.monthrange(year, month)
        month_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

        # Consulta agregada
        query = select(
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        ).where(
            Transaction.user_id == self.user_id,
            or_(
                and_(
                    Transaction.is_fixed == False,
                    Transaction.date >= month_start,
                    Transaction.date <= month_end
                ),
                and_(
                    Transaction.is_fixed == True,
                    Transaction.date <= month_end,
                    or_(
                        Transaction.deleted_at == None,
                        Transaction.deleted_at >= month_start
                    )
                )
            )
        ).group_by(Transaction.type)

        result = await self.db.execute(query)
        rows = result.all()

        income = 0.0
        expenses = 0.0

        for tx_type, total in rows:
            if tx_type == "income":
                income = float(total)
            elif tx_type == "expense":
                expenses = float(total)

        balance = income - expenses
        savings_rate = (income - expenses) / income * 100 if income > 0 else 0.0

        return {
            "month": month,
            "year": year,
            "income": round(income, 2),
            "expenses": round(expenses, 2),
            "balance": round(balance, 2),
            "savings_rate": round(savings_rate, 2),
        }

    async def get_expenses_by_category(
        self,
        month: int | None = None,
        year: int | None = None,
    ) -> list[dict]:
        """
        Obtiene gastos agrupados por categoría.

        Returns:
            Lista de dicts: [{"category": "food", "total": 150.0, "count": 5}, ...]
        """
        now = datetime.now(timezone.utc)
        month = month or now.month
        year = year or now.year

        month_start = datetime(year, month, 1, tzinfo=timezone.utc)
        _, last_day = calendar.monthrange(year, month)
        month_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

        query = select(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        ).where(
            Transaction.user_id == self.user_id,
            Transaction.type == "expense",
            or_(
                and_(
                    Transaction.is_fixed == False,
                    Transaction.date >= month_start,
                    Transaction.date <= month_end
                ),
                and_(
                    Transaction.is_fixed == True,
                    Transaction.date <= month_end,
                    or_(
                        Transaction.deleted_at == None,
                        Transaction.deleted_at >= month_start
                    )
                )
            )
        ).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc())

        result = await self.db.execute(query)

        return [
            {
                "category": row.category,
                "total": round(float(row.total), 2),
                "count": row.count,
            }
            for row in result.all()
        ]

    async def get_fixed_transactions(self) -> list[Transaction]:
        """Obtiene todas las transacciones fijas/recurrentes del usuario."""
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.user_id == self.user_id,
                Transaction.is_fixed == True,
            ).order_by(Transaction.amount.desc())
        )
        return list(result.scalars().all())

    async def get_yearly_summary(self, year: int | None = None) -> dict:
        """
        Obtiene resumen anual completo.

        Returns:
            Dict con resumen por mes y totales anuales
        """
        if year is None:
            year = datetime.now(timezone.utc).year

        # Totales anuales
        query = select(
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        ).where(
            Transaction.user_id == self.user_id,
            func.strftime("%Y", Transaction.date) == str(year),
        ).group_by(Transaction.type)

        result = await self.db.execute(query)
        rows = result.all()

        yearly_income = 0.0
        yearly_expenses = 0.0

        for tx_type, total in rows:
            if tx_type == "income":
                yearly_income = float(total)
            elif tx_type == "expense":
                yearly_expenses = float(total)

        # Resumen mensual
        monthly_query = select(
            func.strftime("%m", Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        ).where(
            Transaction.user_id == self.user_id,
            func.strftime("%Y", Transaction.date) == str(year),
        ).group_by(
            func.strftime("%m", Transaction.date),
            Transaction.type,
        ).order_by("month")

        monthly_result = await self.db.execute(monthly_query)
        monthly_data: dict[str, dict] = {}

        for row in monthly_result.all():
            month = row.month
            if month not in monthly_data:
                monthly_data[month] = {"income": 0.0, "expenses": 0.0}

            if row.type == "income":
                monthly_data[month]["income"] = float(row.total)
            else:
                monthly_data[month]["expenses"] = float(row.total)

        return {
            "year": year,
            "total_income": round(yearly_income, 2),
            "total_expenses": round(yearly_expenses, 2),
            "total_balance": round(yearly_income - yearly_expenses, 2),
            "monthly_breakdown": monthly_data,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Helper function
# ══════════════════════════════════════════════════════════════════════════════

async def get_finance_service(db: AsyncSession, user_id: str) -> FinanceService:
    """Factory para obtener FinanceService."""
    return FinanceService(db, user_id)
