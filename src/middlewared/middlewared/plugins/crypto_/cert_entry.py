from middlewared.schema import Bool, Dict, Int, List, Str


CERT_ENTRY = Dict(
    'certificate_entry',
    Int('id'),
    Int('type'),
    Str('name'),
    Str('certificate', null=True, max_length=None),
    Str('privatekey', null=True, max_length=None, private=True),
    Str('CSR', null=True, max_length=None),
    Str('acme_uri', null=True),
    Dict('domains_authenticators', additional_attrs=True, null=True),
    Int('renew_days'),
    Str('root_path'),
    Dict('acme', additional_attrs=True, null=True),
    Str('certificate_path', null=True),
    Str('privatekey_path', null=True),
    Str('csr_path', null=True),
    Str('cert_type'),
    Bool('expired', null=True),
    List('chain_list', items=[Str('certificate', max_length=None)]),
    Str('country', null=True),
    Str('state', null=True),
    Str('city', null=True),
    Str('organization', null=True),
    Str('organizational_unit', null=True),
    List('san', items=[Str('san_entry')], null=True),
    Str('email', null=True),
    Str('DN', null=True),
    Str('subject_name_hash', null=True),
    Str('digest_algorithm', null=True),
    Str('from', null=True),
    Str('common', null=True, max_length=None),
    Str('until', null=True),
    Str('fingerprint', null=True),
    Str('key_type', null=True),
    Str('internal', null=True),
    Int('lifetime', null=True),
    Int('serial', null=True),
    Int('key_length', null=True),
    Bool('add_to_trusted_store', default=False),
    Bool('chain', null=True),
    Bool('cert_type_existing'),
    Bool('cert_type_CSR'),
    Bool('parsed'),
    Dict('extensions', additional_attrs=True),
)
