from payment.models import Payment, PaymentDetail


def create_test_payment2(insuree_code=None, product_code=None, officer_code=None,
                         link=True, custom_props=None, detail_custom_props=None):
    """
    Creates a Payment and optionally an PaymentDetail
    :param insuree_code: CHF_ID of the insuree to connect in the details
    :param product_code: Product code (insuree+product => policy)
    :param officer_code: code of the officer to include into the payment data
    :param link: if True (default), a PaymentDetail will also be created
    :param custom_props: dictionary of custom values for the Payment, when overriding a foreign key, override the _id
    :param detail_custom_props: dictionary of custom values for the PaymentDetail
    :return: The created Payment and PaymentDetail
    """
    if custom_props is None:
        custom_props = {}
    else:
        custom_props = {k: v for k, v in custom_props.items() if hasattr(Payment, k)}
    if detail_custom_props is None:
        detail_custom_props = {}
    else:
        detail_custom_props = {k: v for k, v in detail_custom_props.items() if hasattr(PaymentDetail, k)}

    payment = Payment.objects.create(
        **{
            "received_amount": "1000",
            "request_date": "2020-01-01",
            "payment_date": "2020-01-02",
            "received_date": "2020-01-03",
            "validity_to": None,
            "officer_code": officer_code,
            "status": Payment.STATUS_UNMATCHED,
            **custom_props
        }
    )
    if link:
        payment_detail = PaymentDetail.objects.create(
            payment=payment,
            audit_user_id=-1,
            validity_from="2019-01-01",
            validity_to=None,
            product_code=product_code,
            insurance_number=insuree_code,
            policy_stage='N',
            amount="1000",
            **detail_custom_props
        )
    else:
        payment_detail = None

    return payment, payment_detail
