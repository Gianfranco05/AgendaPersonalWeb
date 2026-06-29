## ADDED Requirements

### Requirement: finanzas/enums.py exists with required enumerations
The system SHALL provide a `finanzas/enums.py` file containing TransactionType, AccountType, PaymentMethod, and MerchantCategory enumerations.

#### Scenario: TransactionType enum defines INCOME and EXPENSE
- **WHEN** importing TransactionType from finanzas.enums
- **THEN** the enum SHALL have members `INCOME` and `EXPENSE`

#### Scenario: AccountType enum defines all account types
- **WHEN** importing AccountType from finanzas.enums
- **THEN** the enum SHALL have members `CHECKING`, `SAVINGS`, `CREDIT`, and `CASH`

#### Scenario: PaymentMethod enum defines all payment methods
- **WHEN** importing PaymentMethod from finanzas.enums
- **THEN** the enum SHALL have members `CASH`, `DEBIT_CARD`, `CREDIT_CARD`, `TRANSFER`, `CHECK`, and `OTHER`

#### Scenario: MerchantCategory enum defines all merchant categories
- **WHEN** importing MerchantCategory from finanzas.enums
- **THEN** the enum SHALL have members `GROCERY`, `UTILITIES`, `TRANSPORTATION`, `ENTERTAINMENT`, `HEALTHCARE`, `EDUCATION`, `DINING`, `SHOPPING`, `TRAVEL`, `SERVICES`, and `OTHER`

#### Scenario: FinanzasService and TransactionRepository can import enums
- **WHEN** FinanzasService or TransactionReference references TransactionType, AccountType, PaymentMethod, or MerchantCategory
- **THEN** the imports SHALL resolve without ImportError

### Requirement: finanzas/cuentas_routes.py router included in main.py
The system SHALL include the `finanzas/cuentas_routes.py` router in `main.py` under the `/finanzas` prefix so account management endpoints are accessible.

#### Scenario: Cuentas routes are mounted under /finanzas prefix
- **WHEN** the FastAPI application starts
- **THEN** routes defined in `cuentas_routes.py` SHALL be accessible under the `/finanzas` URL prefix

### Requirement: anotaciones/export_routes.py router included in main.py
The system SHALL include the `anotaciones/export_routes.py` router in `main.py` under the `/anotaciones` prefix so note export endpoints are accessible.

#### Scenario: Anotaciones export routes are mounted under /anotaciones prefix
- **WHEN** the FastAPI application starts
- **THEN** routes defined in `anotaciones/export_routes.py` SHALL be accessible under the `/anotaciones` URL prefix

### Requirement: eventos/export_routes.py router included in main.py
The system SHALL include the `eventos/export_routes.py` router in `main.py` under the `/eventos` prefix so event export endpoints are accessible.

#### Scenario: Eventos export routes are mounted under /eventos prefix
- **WHEN** the FastAPI application starts
- **THEN** routes defined in `eventos/export_routes.py` SHALL be accessible under the `/eventos` URL prefix

### Requirement: All imports resolve without errors when app starts
The system SHALL ensure that all module imports resolve correctly when the FastAPI application starts with `uvicorn main:app`.

#### Scenario: Application starts without ImportError
- **WHEN** running `uvicorn main:app` from the backend directory
- **THEN** the application SHALL start successfully without any import-related errors

#### Scenario: All 6 modules are importable
- **WHEN** the application boots
- **THEN** modules auth, finanzas, anotaciones, eventos, metas, and ajustes SHALL all be successfully imported
