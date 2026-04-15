"""
MarcoAI – Finance Tools for LangGraph Agent (Fase 7)
══════════════════════════════════════════════════════════════════════════════

Herramientas que el Agente de Finanzas puede invocar para realizar
operaciones sobre transacciones financieras.

Cada herramienta es una función async decorada con @tool de LangChain.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from langchain_core.tools import tool

from app.db.models import User
from app.services.finance_service import CATEGORIES_EXPENSE, CATEGORIES_INCOME, FinanceService

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  Helper para obtener el servicio de finanzas
# ══════════════════════════════════════════════════════════════════════════════

async def _get_finance_service(db, user: User) -> FinanceService:
    """Obtiene el FinanceService para el usuario actual."""
    return FinanceService(db, user.id)


# ══════════════════════════════════════════════════════════════════════════════
#  Herramientas del Agente de Finanzas
# ══════════════════════════════════════════════════════════════════════════════

@tool
async def register_expense(
    db,
    user: User,
    amount: float,
    category: str,
    description: str,
    date: str | None = None,
) -> str:
    """
    Registra un nuevo gasto en el sistema.

    Args:
        amount: Cantidad del gasto (siempre positiva, ej: 45.50)
        category: Categoría del gasto (alimentacion, transporte, ocio, tecnologia, salud, hogar, servicios, compras, otros)
        description: Descripción breve del gasto
        date: Fecha en formato ISO (YYYY-MM-DD) o "hoy" por defecto

    Returns:
        Mensaje de confirmación con el gasto registrado.
    """
    try:
        service = await _get_finance_service(db, user)

        # Parsear fecha
        if date and date.lower() != "hoy":
            tx_date = datetime.fromisoformat(date)
        else:
            tx_date = datetime.now(timezone.utc)

        # Normalizar categoría
        category = category.lower().strip()
        if category not in CATEGORIES_EXPENSE:
            category = "otros"

        transaction = await service.create_transaction(
            tx_type="expense",
            amount=abs(amount),
            category=category,
            description=description,
            date=tx_date,
        )

        return f"✅ Gasto registrado: **{amount}€** en **{category}**\n\n📝 {description}"

    except Exception as exc:
        logger.exception("Error en register_expense")
        return f"❌ Error al registrar el gasto: {exc}"


@tool
async def register_income(
    db,
    user: User,
    amount: float,
    category: str,
    description: str,
    date: str | None = None,
) -> str:
    """
    Registra un nuevo ingreso en el sistema.

    Args:
        amount: Cantidad del ingreso
        category: Categoría (salario, freelance, inversiones, regalo, otros)
        description: Descripción del ingreso
        date: Fecha en formato ISO o "hoy"

    Returns:
        Mensaje de confirmación.
    """
    try:
        service = await _get_finance_service(db, user)

        if date and date.lower() != "hoy":
            tx_date = datetime.fromisoformat(date)
        else:
            tx_date = datetime.now(timezone.utc)

        category = category.lower().strip()
        if category not in CATEGORIES_INCOME:
            category = "otros"

        transaction = await service.create_transaction(
            tx_type="income",
            amount=abs(amount),
            category=category,
            description=description,
            date=tx_date,
        )

        return f"✅ Ingreso registrado: **{amount}€** de **{category}**\n\n📝 {description}"

    except Exception as exc:
        logger.exception("Error en register_income")
        return f"❌ Error al registrar el ingreso: {exc}"


@tool
async def get_monthly_balance(
    db,
    user: User,
    month: int | None = None,
    year: int | None = None,
) -> str:
    """
    Obtiene el balance mensual del usuario (ingresos - gastos).

    Args:
        month: Mes (1-12), por defecto el actual
        year: Año, por defecto el actual

    Returns:
        Texto formateado con el resumen del balance mensual.
    """
    try:
        service = await _get_finance_service(db, user)
        balance = await service.get_monthly_balance(month, year)

        month_name = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ][balance["month"] - 1]

        emoji = "🟢" if balance["balance"] >= 0 else "🔴"

        return f"""\
{emoji} **Balance de {month_name} {balance["year"]}**

| Concepto | Cantidad |
|----------|----------|
| Ingresos | {balance["income"]:,.2f} € |
| Gastos   | {balance["expenses"]:,.2f} € |
| **Balance** | **{balance["balance"]:,.2f} €** |

💡 Tasa de ahorro: {balance["savings_rate"]:.1f}%"""

    except Exception as exc:
        logger.exception("Error en get_monthly_balance")
        return f"❌ Error al obtener el balance: {exc}"


@tool
async def get_expenses_by_category(
    db,
    user: User,
    month: int | None = None,
    year: int | None = None,
) -> str:
    """
    Obtiene los gastos desglosados por categoría.

    Args:
        month: Mes (1-12), por defecto el actual
        year: Año, por defecto el actual

    Returns:
        Texto formateado con la lista de categorías ordenadas por total.
    """
    try:
        service = await _get_finance_service(db, user)
        categories = await service.get_expenses_by_category(month, year)

        if not categories:
            return "No hay gastos registrados este mes."

        month_name = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ][(month or datetime.now().month) - 1]

        lines = [f"📊 **Gastos por categoría - {month_name}**\n"]

        total = sum(c["total"] for c in categories)

        for cat in categories:
            percentage = (cat["total"] / total * 100) if total > 0 else 0
            bar_length = int(percentage / 5)
            bar = "█" * bar_length + "░" * (20 - bar_length)

            category_emoji = {
                "alimentacion": "🍔",
                "transporte": "🚗",
                "ocio": "🎬",
                "tecnologia": "💻",
                "salud": "🏥",
                "hogar": "🏠",
                "servicios": "💡",
                "compras": "🛍️",
                "otros": "📦",
            }.get(cat["category"], "📦")

            lines.append(
                f"{category_emoji} **{cat['category'].capitalize()}**: "
                f"{cat['total']:,.2f}€ ({percentage:.0f}%)\n`{bar}`"
            )

        lines.append(f"\n**Total**: {total:,.2f}€")

        return "\n".join(lines)

    except Exception as exc:
        logger.exception("Error en get_expenses_by_category")
        return f"❌ Error al obtener gastos por categoría: {exc}"


@tool
async def list_recent_transactions(
    db,
    user: User,
    limit: int = 10,
    tx_type: Literal["income", "expense", "all"] = "all",
) -> str:
    """
    Lista las transacciones recientes del usuario.

    Args:
        limit: Número máximo de transacciones a mostrar (default: 10)
        tx_type: Filtrar por tipo: "income", "expense", o "all"

    Returns:
        Texto formateado con la lista de transacciones.
    """
    try:
        service = await _get_finance_service(db, user)

        tx_type_filter = None if tx_type == "all" else tx_type
        transactions = await service.list_transactions(limit=limit, tx_type=tx_type_filter)

        if not transactions:
            return "No hay transacciones recientes."

        lines = ["📋 **Últimas transacciones:**\n"]

        for tx in transactions:
            emoji = "💰" if tx.type == "income" else "💸"
            sign = "+" if tx.type == "income" else "-"
            date_str = tx.date.strftime("%d/%m")

            lines.append(
                f"{emoji} **{date_str}** {sign}{tx.amount:,.2f}€\n"
                f"   _{tx.description}_ ({tx.category})"
            )

        return "\n".join(lines)

    except Exception as exc:
        logger.exception("Error en list_recent_transactions")
        return f"❌ Error al listar transacciones: {exc}"


@tool
async def get_fixed_transactions(db, user: User) -> str:
    """
    Obtiene la lista de gastos e ingresos fijos recurrentes.

    Returns:
        Texto formateado con la lista de transacciones fijas.
    """
    try:
        service = await _get_finance_service(db, user)
        transactions = await service.get_fixed_transactions()

        if not transactions:
            return "No tienes transacciones fijas registradas."

        fixed_expenses = [tx for tx in transactions if tx.type == "expense"]
        fixed_income = [tx for tx in transactions if tx.type == "income"]

        lines = ["📌 **Transacciones Fijas**\n"]

        if fixed_expenses:
            lines.append("**Gastos Fijos:**")
            for tx in fixed_expenses:
                recurrence = tx.recurrence or "mensual"
                lines.append(f"• {tx.description}: **{tx.amount:,.2f}€** ({recurrence})")

        if fixed_income:
            lines.append("\n**Ingresos Fijos:**")
            for tx in fixed_income:
                recurrence = tx.recurrence or "mensual"
                lines.append(f"• {tx.description}: **{tx.amount:,.2f}€** ({recurrence})")

        total_fixed = sum(tx.amount for tx in fixed_expenses)
        lines.append(f"\n💡 **Total gastos fijos/mes**: {total_fixed:,.2f}€")

        return "\n".join(lines)

    except Exception as exc:
        logger.exception("Error en get_fixed_transactions")
        return f"❌ Error al obtener transacciones fijas: {exc}"


@tool
async def delete_transaction(db, user: User, transaction_id: str) -> str:
    """
    Elimina una transacción por su ID.

    Args:
        transaction_id: ID de la transacción a eliminar

    Returns:
        Mensaje de confirmación o error.
    """
    try:
        service = await _get_finance_service(db, user)
        deleted = await service.delete_transaction(transaction_id)

        if deleted:
            return "✅ Transacción eliminada correctamente."
        return "❌ No se encontró la transacción con ese ID."

    except Exception as exc:
        logger.exception("Error en delete_transaction")
        return f"❌ Error al eliminar la transacción: {exc}"


# ══════════════════════════════════════════════════════════════════════════════
#  Exportar todas las herramientas
# ══════════════════════════════════════════════════════════════════════════════

FINANCE_TOOLS = [
    register_expense,
    register_income,
    get_monthly_balance,
    get_expenses_by_category,
    list_recent_transactions,
    get_fixed_transactions,
    delete_transaction,
]
