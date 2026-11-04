"""Regenera los archivos ficticios de este directorio (todo inventado: no hay
datos reales). Uso: python make_fixtures.py"""

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

HERE = Path(__file__).parent

MP_RELEASE_EN = """DATE,SOURCE_ID,EXTERNAL_REFERENCE,RECORD_TYPE,DESCRIPTION,NET_CREDIT_AMOUNT,NET_DEBIT_AMOUNT,GROSS_AMOUNT,BALANCE_AMOUNT,CURRENCY
2026-10-01T00:00:00-04:00,,,initial_available_balance,,,,,15000.00,ARS
2026-10-02T10:15:30-04:00,1001,REF-A,release,payment,2500.50,0.00,2600.00,,ARS
2026-10-03T23:30:00-04:00,1002,,release,payout,0.00,1000.00,1000.00,,ARS
2026-10-05T09:00:00-04:00,1003,,release,tax_iva,0.00,15.25,,,ARS
2026-10-31T23:59:59-04:00,,,total,,2500.50,1015.25,,,ARS
"""

# Punto y coma, BOM, decimales es-AR, encabezados en ingles.
MP_RELEASE_SEMI = (
    "﻿DATE;SOURCE_ID;EXTERNAL_REFERENCE;RECORD_TYPE;DESCRIPTION;NET_CREDIT_AMOUNT;NET_DEBIT_AMOUNT;GROSS_AMOUNT;BALANCE_AMOUNT;CURRENCY\n"
    "2026-10-02T10:15:30-04:00;2001;;release;payment;1.234,56;0,00;1.300,00;;ARS\n"
    "2026-10-04T18:00:00-04:00;2002;;release;refund;0,00;200,00;200,00;;ARS\n"
)

MP_ACCOUNT = """TRANSACTION_DATE,SOURCE_ID,DESCRIPTION,TRANSACTION_TYPE,TRANSACTION_AMOUNT,SETTLEMENT_NET_AMOUNT,SETTLEMENT_CURRENCY
2026-10-06T12:00:00-04:00,3001,Venta remera,SETTLEMENT,5000.00,4800.00,ARS
2026-10-07T08:30:00-04:00,3002,Retiro a CBU,WITHDRAWAL,3000.00,-3000.00,ARS
2026-10-08T08:30:00-04:00,3003,Devolucion,REFUND,500.00,,ARS
"""

BANCO_CP1252 = (
    "Banco Ejemplo S.A.;;;;\n"
    "Cuenta Corriente 0000-0000;;;;\n"
    ";;;;\n"
    "Fecha;Concepto;Débito;Crédito;Saldo\n"
    "01/10/2026;COMPRA COTO SUC 12;1.234,56;;98.765,44\n"
    "02/10/2026;Acreditación sueldo;;250.000,00;348.765,44\n"
    "13/10/2026;Pago servicio Edenor;8.500,00;;340.265,44\n"
)

INYECCION = """fecha,descripcion,monto
2026-10-01,"=HYPERLINK(""http://x"",""clic"")",-100
2026-10-02,+1+1,-50
2026-10-03,@SUM(A1),200
"""


def main():
    (HERE / "mp_release_en.csv").write_text(MP_RELEASE_EN, encoding="utf-8", newline="\n")
    (HERE / "mp_release_es_punto_y_coma.csv").write_text(MP_RELEASE_SEMI, encoding="utf-8", newline="\n")
    (HERE / "mp_account_money.csv").write_text(MP_ACCOUNT, encoding="utf-8", newline="\n")
    (HERE / "banco_generico_cp1252.csv").write_bytes(BANCO_CP1252.encode("cp1252"))
    (HERE / "inyeccion_formulas.csv").write_text(INYECCION, encoding="utf-8", newline="\n")

    wb = Workbook()
    ws = wb.active
    ws.append(["Fecha", "Descripción", "Importe", "Moneda"])
    ws.append([datetime(2026, 10, 3, 14, 5), "Supermercado Disco", -4321.5, "$"])
    ws.append([datetime(2026, 10, 4), "Sueldo", 300000, "$"])
    ws.append([datetime(2026, 10, 5), "Compra dólares", -100, "U$S"])
    wb.save(HERE / "billetera_monto_signo.xlsx")


if __name__ == "__main__":
    main()
