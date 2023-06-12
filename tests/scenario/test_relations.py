import json

from scenario import Relation, State


def test_no_relations(ctx):
    state_out = ctx.run("install", State(leader=True))
    assert state_out.status.unit.name == "waiting"


def test_truststore_csr_flow(ctx):
    """Verify that csrs sent to truststore over relation data get relayed to tls-certificates unit data."""
    truststore_relation = Relation(
        "tls-truststore",
        remote_units_data={
            0: {"certificate_signing_request": "123"},  # traefik/0
            1: {"certificate_signing_request": "1234"},  # traefik/1
            2: {"certificate_signing_request": "12345"},  # traefik/2
        },
    )
    truststore_relation_2 = Relation(
        "tls-truststore",
        remote_app_name="alertmanager",
        remote_units_data={
            0: {"certificate_signing_request": "abc"},  # alertmanager/0
            1: {"certificate_signing_request": "abc4"},  # alertmanager/1
            2: {"certificate_signing_request": "abc45"},  # alertmanager/2
        },
    )
    tls_certs_relation = Relation(
        "tls-certificates",
    )
    state_out = ctx.run(
        truststore_relation.changed_event,
        State(leader=True, relations=[
            truststore_relation,
            truststore_relation_2,
            tls_certs_relation]),
    )

    assert state_out.status.unit.name == "active"
    tls_certs_out = state_out.get_relations("tls-certificates")[0]
    published_csrs = json.loads(tls_certs_out.local_unit_data["certificate_signing_requests"])
    assert len(published_csrs) == 6

    for csr in (
            {"certificate_signing_request": "123"},
            {"certificate_signing_request": "1234"},
            {"certificate_signing_request": "12345"},
            {"certificate_signing_request": "abc"},
            {"certificate_signing_request": "abc4"},
            {"certificate_signing_request": "abc45"},
    ):
        assert csr in published_csrs


def test_tls_certificates_flow(ctx):
    # Verify that certificates sent to truststore over relation data by tls-certificates
    # get relayed to tls-truststore app data.

    truststore_relation = Relation(
        "tls-truststore",
        remote_units_data={
            0: {"certificate_signing_request": "123"},
            1: {"certificate_signing_request": "1234"},
            2: {"certificate_signing_request": "12345"},
        },
    )
    truststore_relation_2 = Relation(
        "tls-truststore",
        remote_app_name="alertmanager",
        remote_units_data={
            0: {"certificate_signing_request": "abc"},  # alertmanager/0
            1: {"certificate_signing_request": "abc4"},  # alertmanager/1
            2: {"certificate_signing_request": "abc45"},  # alertmanager/2
        },
    )
    tls_certs_relation = Relation(
        "tls-certificates",
        local_unit_data={
            "certificate_signing_requests": json.dumps(
                [
                    {"certificate_signing_request": "123"},
                    {"certificate_signing_request": "1234"},
                    {"certificate_signing_request": "12345"},
                ]
            )
        },
        remote_app_data={
            "certificates": json.dumps(
                [
                    {
                        "certificate": "foo",
                        "certificate_signing_request": "123",
                        "ca": "bar",
                        "chain": ["1", "2"],
                    },
                    {
                        "certificate": "foos",
                        "certificate_signing_request": "1234",
                        "ca": "baz",
                        "chain": ["1", "3"],
                    },
                    {
                        "certificate": "alertmgrcert",
                        "certificate_signing_request": "abc4",
                        "ca": "bax",
                        "chain": ["4", "3"],
                    },
                ]
            )
        },
    )

    state_out = ctx.run(
        tls_certs_relation.changed_event,
        State(leader=True, relations=[
            truststore_relation,
            truststore_relation_2,
            tls_certs_relation
        ]),
    )

    assert state_out.status.unit.name == "active"
    truststore_out = state_out.get_relations("tls-truststore")[0]
    trust = json.loads(truststore_out.local_app_data["trust"])
    assert len(trust) == 2

    truststore_out_2 = state_out.get_relations("tls-truststore")[1]
    trust2 = json.loads(truststore_out_2.local_app_data["trust"])
    assert len(trust2) == 1

