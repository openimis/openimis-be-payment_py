from django.test import TestCase
from django.db import connection

from contribution.test_helpers import create_test_premium
from core.test_helpers import create_test_officer
from insuree.test_helpers import create_test_insuree
from location.test_helpers import create_test_location
from medical.test_helpers import create_test_service
from medical_pricelist.test_helpers import add_service_to_hf_pricelist
from payment.services import legacy_match_payment, validate_payment_detail, PAYMENT_DETAIL_REJECTION_INSURANCE_NB, \
    PAYMENT_DETAIL_REJECTION_PRODUCT_CODE, PAYMENT_DETAIL_REJECTION_INSURANCE_NB_INVALID, \
    PAYMENT_DETAIL_REJECTION_POLICY_NOT_FOUND, PAYMENT_DETAIL_REJECTION_PRODUCT_NOT_ALLOWED, \
    PAYMENT_DETAIL_REJECTION_PRODUCT_LOCATION, match_payment
from payment.test_helpers import create_test_payment2
from policy.models import Policy
from policy.test_helpers import create_test_policy2
from product.test_helpers import create_test_product, create_test_product_service


# noinspection DuplicatedCode
class PaymentServiceTestCase(TestCase):
    region1 = None
    region2 = None

    def setUp(self):
        super().setUp()
        self.region1 = create_test_location('R', custom_props={'code': 'R1', 'name': 'TADA'})
        self.region2 = create_test_location('R', custom_props={'code': 'R2', 'name': 'Tahida'})

    def test_call_to_legacy(self):
        # TODO: Add matching test and procedure for PostgreSQL
        if not connection.vendor == 'mssql':
            self.skipTest("This test can only be executed for MSSQL database")
        officer = create_test_officer(custom_props={"code": "TSTSIMP1"})
        insuree = create_test_insuree(custom_props={"chf_id": "paysimp"})
        product = create_test_product("ELI1")
        (policy, insuree_policy) = create_test_policy2(product, insuree, custom_props={
            "value": 1000, "status": Policy.STATUS_IDLE})
        service = create_test_service("A")
        svc_pl_detail = add_service_to_hf_pricelist(service)
        product_service = create_test_product_service(product, service, custom_props={"limit_no_adult": 20})
        premium = create_test_premium(policy_id=policy.id, with_payer=False)
        payment, payment_detail = create_test_payment2(
            insuree_code=insuree.chf_id,
            product_code=product.code,
            officer_code=officer.code,
        )

        legacy_match_payment(payment.id, -1)
        # errors = validate_payment_detail(payment_detail)

        payment_detail.refresh_from_db()
        policy.refresh_from_db()
        self.assertIsNotNone(payment_detail.premium)
        self.assertEqual(payment_detail.premium, premium)

        payment_detail.delete()
        payment.delete()
        premium.delete()
        product_service.delete()
        svc_pl_detail.delete()
        service.delete()
        policy.insuree_policies.all().delete()
        policy.delete()
        product.delete()
        officer.delete()

    def test_validate_simple(self):
        officer = create_test_officer(custom_props={"code": "TSTSIMP1"})
        insuree = create_test_insuree(custom_props={"chf_id": "paysimp"})
        product = create_test_product("ELI1")
        (policy, insuree_policy) = create_test_policy2(product, insuree, custom_props={
            "value": 1000, "status": Policy.STATUS_IDLE})

        premium = create_test_premium(policy_id=policy.id, with_payer=False)
        payment, payment_detail = create_test_payment2(
            insuree_code=insuree.chf_id,
            product_code=product.code,
            officer_code=officer.code,
        )

        errors = validate_payment_detail(payment_detail)

        self.assertEqual(len(errors), 0)
        self.assertIsNotNone(payment_detail.policy)
        self.assertIsNotNone(payment_detail.product)
        self.assertIsNotNone(payment_detail.insuree)

        payment_detail.delete()
        payment.delete()
        premium.delete()
        policy.insuree_policies.all().delete()
        policy.delete()
        product.delete()
        officer.delete()

    def test_validate_no_insuree(self):
        officer = create_test_officer(custom_props={"code": "TSTSIMP1"})
        insuree = create_test_insuree(custom_props={"chf_id": "paysimp"})
        product = create_test_product("ELI1")
        (policy, insuree_policy) = create_test_policy2(product, insuree, custom_props={
            "value": 1000, "status": Policy.STATUS_IDLE})
        premium = create_test_premium(policy_id=policy.id, with_payer=False)
        payment, payment_detail = create_test_payment2(
            insuree_code=None,
            product_code=product.code,
            officer_code=officer.code,
        )

        errors = validate_payment_detail(payment_detail)

        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[0]["code"], PAYMENT_DETAIL_REJECTION_INSURANCE_NB)

        payment_detail.delete()
        payment.delete()
        premium.delete()

        policy.insuree_policies.all().delete()
        policy.delete()
        product.delete()
        officer.delete()

    def test_validate_no_product_code(self):
        officer = create_test_officer(custom_props={"code": "TSTSIMP1"})
        insuree = create_test_insuree(custom_props={"chf_id": "paysimp"})
        product = create_test_product("ELI1")
        (policy, insuree_policy) = create_test_policy2(product, insuree, custom_props={
            "value": 1000, "status": Policy.STATUS_IDLE})
        premium = create_test_premium(policy_id=policy.id, with_payer=False)
        payment, payment_detail = create_test_payment2(
            insuree_code=insuree.chf_id,
            product_code=None,
            officer_code=officer.code,
        )

        errors = validate_payment_detail(payment_detail)

        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[0]["code"], PAYMENT_DETAIL_REJECTION_PRODUCT_CODE)

        payment_detail.delete()
        payment.delete()
        premium.delete()
        policy.insuree_policies.all().delete()
        policy.delete()
        product.delete()
        officer.delete()

    def test_validate_invalid_insuree_number(self):
        officer = create_test_officer(custom_props={"code": "TSTSIMP1"})
        insuree = create_test_insuree(custom_props={"chf_id": "paysimp"})
        product = create_test_product("ELI1")
        (policy, insuree_policy) = create_test_policy2(product, insuree, custom_props={
            "value": 1000, "status": Policy.STATUS_IDLE})
        premium = create_test_premium(policy_id=policy.id, with_payer=False)
        payment, payment_detail = create_test_payment2(
            insuree_code="xxxxxx",
            product_code=product.code,
            officer_code=officer.code,
        )

        errors = validate_payment_detail(payment_detail)

        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[0]["code"], PAYMENT_DETAIL_REJECTION_INSURANCE_NB_INVALID)

        payment_detail.delete()
        payment.delete()
        premium.delete()
        policy.insuree_policies.all().delete()
        policy.delete()
        product.delete()
        officer.delete()

    def test_validate_invalid_policy(self):
        officer = create_test_officer(custom_props={"code": "TSTSIMP1"})
        insuree = create_test_insuree(custom_props={"chf_id": "paysimp"})
        product = create_test_product("ELI1")
        (policy, insuree_policy) = create_test_policy2(
            product, insuree, valid=False,  # !! INVALID POLICY
            custom_props={"value": 1000, "status": Policy.STATUS_IDLE})
        premium = create_test_premium(policy_id=policy.id, with_payer=False)
        payment, payment_detail = create_test_payment2(
            insuree_code=insuree.chf_id,
            product_code=product.code,
            officer_code=officer.code,
        )

        errors = validate_payment_detail(payment_detail)

        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[0]["code"], PAYMENT_DETAIL_REJECTION_POLICY_NOT_FOUND)

        payment_detail.delete()
        payment.delete()
        premium.delete()
        policy.insuree_policies.all().delete()
        policy.delete()
        product.delete()
        officer.delete()

        officer = create_test_officer(custom_props={"code": "TSTSIMP1", "location": self.region1})
        insuree = create_test_insuree(custom_props={"chf_id": "paysimp"},
                                      family_custom_props={"location": self.region1})  # Family in R1 !
        product = create_test_product("ELI1", custom_props={"location": insuree.family.location.parent.parent.parent})  # Product in R2 !
        (policy, insuree_policy) = create_test_policy2(
            product, insuree,
            custom_props={"value": 1000, "status": Policy.STATUS_IDLE})
        premium = create_test_premium(policy_id=policy.id, with_payer=False)
        payment, payment_detail = create_test_payment2(
            insuree_code=insuree.chf_id,
            product_code=product.code,
            officer_code=officer.code,
        )

        errors = validate_payment_detail(payment_detail)

        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[0]["code"], PAYMENT_DETAIL_REJECTION_PRODUCT_LOCATION)

        payment_detail.delete()
        payment.delete()
        premium.delete()

        policy.insuree_policies.all().delete()
        policy.delete()
        product.delete()
        officer.delete()

    def test_validate_invalid_product_location(self):
        officer = create_test_officer(custom_props={"code": "TSTSIMP1"})
        insuree = create_test_insuree(custom_props={"chf_id": "paysimp"},
                                      family_custom_props={"location": self.region1})  # Family in R1 !
        product = create_test_product("ELI1", custom_props={"location": self.region2})  # Product in R2 !
        (policy, insuree_policy) = create_test_policy2(
            product, insuree,
            custom_props={"value": 1000, "status": Policy.STATUS_IDLE})

        premium = create_test_premium(policy_id=policy.id, with_payer=False)
        payment, payment_detail = create_test_payment2(
            insuree_code=insuree.chf_id,
            product_code=product.code,
            officer_code=officer.code,
        )

        errors = validate_payment_detail(payment_detail)

        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[0]["code"], PAYMENT_DETAIL_REJECTION_PRODUCT_NOT_ALLOWED)

        payment_detail.delete()
        payment.delete()
        premium.delete()
        policy.insuree_policies.all().delete()
        policy.delete()
        product.delete()
        officer.delete()

    def test_match_payment_simple(self):
        officer = create_test_officer(custom_props={"code": "TSTSIMP1"})
        insuree = create_test_insuree(custom_props={"chf_id": "paysimp"})
        product = create_test_product("ELI1")
        (policy, insuree_policy) = create_test_policy2(product, insuree, custom_props={
            "value": 1000, "status": Policy.STATUS_IDLE})
        premium = create_test_premium(policy_id=policy.id, with_payer=False)
        payment, payment_detail = create_test_payment2(
            insuree_code=insuree.chf_id,
            product_code=product.code,
            officer_code=officer.code,
        )

        match_payment(payment=payment, audit_user_id=-1)

        payment_detail.refresh_from_db()
        self.assertEqual(payment_detail.premium, premium)

        payment_detail.delete()
        payment.delete()
        premium.delete()
        policy.insuree_policies.all().delete()
        policy.delete()
        product.delete()
        officer.delete()
