## ADDED Requirements

### Requirement: Renew a matured fixed term
The system SHALL expose `POST /api/v1/finance/investments/{id}/renew` for the current user's investments. Renewal SHALL only be allowed for an `active` investment with `asset_type = "fixed_term"` whose `maturity_date` is on or before the user's local date and that has not been renewed before. The request SHALL include `mode` (`principal_and_interest` or `principal_only`), a new `interest_rate_tna` (> 0, ≤ 999,9999) and either `term_days` (1–3650) or `maturity_date`; it MAY include `start_date` (default the local date; it SHALL be between the previous maturity date and the local date), `amount_collected` (default the computed amount at maturity) and `timezone_offset_minutes`. In a single database transaction the system SHALL close the current investment setting `current_value = amount_collected`, and create a new `fixed_term` investment copying name, institution, currency, notes, maturity notification preference and offset, with `invested_amount` equal to `amount_collected` (`principal_and_interest`) or to the previous `invested_amount` (`principal_only`), the new rate and dates, and `renewed_from_id` pointing to the previous investment. The response SHALL contain both investments.

#### Scenario: Renew capital plus interest
- **WHEN** a fixed term of 1.000.000 ARS at 30 % TNA for 30 days matured today and the user renews it with `mode = "principal_and_interest"`, TNA 28 and `term_days = 30`
- **THEN** the old investment SHALL be `closed` with `current_value = 1024657.53`, and a new active fixed term SHALL exist with `invested_amount = 1024657.53`, TNA 28, `start_date` today, maturity in 30 days and `renewed_from_id` = old id

#### Scenario: Renew only the principal
- **WHEN** the same fixed term is renewed with `mode = "principal_only"`
- **THEN** the new fixed term SHALL have `invested_amount = 1000000` and the old one SHALL be closed

#### Scenario: Collected amount edited
- **WHEN** the user renews with `amount_collected = 1024600`
- **THEN** that amount SHALL be used instead of the computed one

#### Scenario: Not yet matured
- **WHEN** the user tries to renew a fixed term that matures tomorrow in their local date
- **THEN** the API SHALL return 422 and nothing SHALL change

#### Scenario: Not a fixed term, closed or another user's
- **WHEN** the target is not a fixed term or is closed
- **THEN** the API SHALL return 422, and when it belongs to another user it SHALL return 404

#### Scenario: Renewed twice
- **WHEN** the same renewal request is sent twice (offline queue retry)
- **THEN** only one new investment SHALL exist and the second request SHALL return 409

#### Scenario: Invalid inputs
- **WHEN** the request has a start date before the previous maturity or after today, mismatching `term_days` and `maturity_date`, a negative interest in `principal_only`, or an amount above 9.999.999.999,99
- **THEN** the API SHALL return 422 with a Spanish message, never 500

### Requirement: Interest withdrawn as optional income
When renewing with `mode = "principal_only"` and `register_interest_income = true`, the system SHALL create, in the same database transaction, an `income` transaction for the interest (`amount_collected − previous invested_amount`, only if greater than zero) dated on the new `start_date`, with `product_name = "Interés plazo fijo: {name}"` and the optional own category, bank account and payment method sent in the request (default payment method `transfer`). Without that flag no transaction SHALL be created.

#### Scenario: Register the interest
- **WHEN** a 1.000.000 fixed term that paid 1.024.657,53 is renewed with `principal_only` and `register_interest_income = true`
- **THEN** an income transaction of 24.657,53 SHALL be created and its id returned in the response

#### Scenario: Do not register
- **WHEN** the same renewal is sent without `register_interest_income`
- **THEN** no transaction SHALL be created

#### Scenario: Foreign category
- **WHEN** `income_category_id` belongs to another user
- **THEN** the API SHALL return 404 and the renewal SHALL NOT happen

### Requirement: Renewal history and consistency
Investment responses SHALL include `renewed_from_id`, `renewed_to_id` and `can_renew`. `GET /api/v1/finance/investments/{id}/renewals` SHALL return the whole renewal chain containing that investment, ordered from oldest to newest (at most 100 items), with each term's dates, principal, rate and interest, plus the accumulated interest. Reopening an investment that has a renewal SHALL return 422. Deleting the previous investment SHALL keep the renewal with `renewed_from_id = null`; deleting the renewal SHALL leave the previous one closed and reopenable.

#### Scenario: Three renewals
- **WHEN** a fixed term was renewed three times and the user requests the renewals of any of them
- **THEN** the API SHALL return the four terms in chronological order

#### Scenario: Reopen a renewed investment
- **WHEN** the user tries to set `status = "active"` on an investment that was renewed
- **THEN** the API SHALL return 422

#### Scenario: Maturity notices after renewal
- **WHEN** a fixed term is renewed
- **THEN** the closed one SHALL no longer receive maturity notices and the new one SHALL receive them for its own maturity date
