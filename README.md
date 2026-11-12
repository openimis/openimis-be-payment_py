# openIMIS Backend Payment reference module
This repository holds the files of the openIMIS Backend Payment reference module. It is dedicated to be deployed as a module of [openimis-be_py](https://github.com/openimis/openimis-be_py).

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## Code climat (develop branch)

[![Maintainability](https://img.shields.io/codeclimate/maintainability/openimis/openimis-be-policy_py.svg)](https://codeclimate.com/github/openimis/openimis-be-contribution_py/maintainability)
[![Test Coverage](https://img.shields.io/codeclimate/coverage/openimis/openimis-be-contribution_py.svg)](https://codeclimate.com/github/openimis/openimis-be-contribution_py)

## ORM mapping:
* tblPaymentType > PaymentType
* tblPayment > Payment

## Row security
* `PaymentDetail`: as visible as its premium (`ParentScope("premium", allow_null=True)`); a detail not matched to a premium yet stays visible to authenticated users.
* `Payment`: visible when one of its details is visible, or when none of its details is matched to a premium yet. Anonymous users see nothing.
* `payments`, `paymentDetails` and `paymentsByPremiums` are filtered through these rules; update, delete and premium matching only reach rows the user may see. The `id` mutation input is ignored: the target is the `uuid`.

## Listened Django Signals
None

## Services
None

## Reports (template can be overloaded via report.ReportDefinition)
None

## GraphQL Queries
None

## GraphQL Mutations - each mutation emits default signals and return standard error lists (cfr. openimis-be-core_py)
None

## Configuration options (can be changed via core.ModuleConfiguration)
None

## openIMIS Modules Dependencies
