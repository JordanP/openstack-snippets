import collections
import re

UUID4 = r'[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}'

REPLACEMENTS_LIST = [
    (r'/AUTH_[a-f0-9]{32}', '/{account}'),     # Normalize Swift account

    (r'/members/[a-f0-9]{32}', '/members/{member_id}'),
    (r'/shared-images/[a-f0-9]{32}', '/shared-images/{owner_id}'),

    (r'/tenants/[a-f0-9]{32}', '/tenants/{project_id}'),
    (r'/projects/[a-f0-9]{32}', '/projects/{project_id}'),
    (r'/domains/[a-f0-9]{32}', '/domains/{domain_id}'),
    (r'/groups/[a-f0-9]{32}', '/groups/{group_id}'),
    (r'/services/[a-f0-9]{32}', '/services/{service_id}'),
    (r'/endpoints/[a-f0-9]{32}', '/endpoints/{endpoint_id}'),
    (r'/tokens/[a-f0-9]{32}', '/tokens/{domain_id}'),
    (r'/policies/[a-f0-9]{32}', '/policies/{policy_id}'),
    (r'/trusts/[a-f0-9]{32}', '/trusts/{trust_id}'),
    (r'/regions/[a-f0-9]{32}', '/regions/{region_id}'),
    (r'/roles/OS-KSADM/[a-f0-9]{32}', '/roles/OS-KSADM/{role_id}'),
    (r'/roles/[a-f0-9]{32}', '/roles/{domain_id}'),
    (r'/users/[a-f0-9]{32}', '/users/{user_id}'),
    (r'/credentials/[a-f0-9]{32,}', '/credentials/{credential_id}'),
    (r'/credentials/OS-EC2/[a-f0-9]{32}', '/credentials/OS-EC2/{user_id}'),

    (r'/volumes/'+UUID4, '/volumes/{volume_id}'),
    (r'/snapshots/' + UUID4, '/snapshots/{snapshot_id}'),
    (r'/backups/' + UUID4, '/backups/{backup_id}'),
    (r'/types/' + UUID4, '/types/{volume_type}'),
    (r'/extra_specs/' + UUID4, '/extra_specs/{extra_spec_id}'),
    (r'/qos-specs/' + UUID4, '/qos-specs/{qos_id}'),
    (r'/os-volume-transfer/' + UUID4, '/os-volume-transfer/{transfer_id}'),
    (r'/messages/' + UUID4, '/messages/{message_id}'),

    (r'/servers/(' + UUID4 + '|:server_id|:\(id\))', '/servers/{server_id}'),
    (r'/os-volumes/(' + UUID4 + '|:\(id\))', '/os-volumes/{volume_id}'),
    (r'/os-fixed-ips/(' + UUID4 + '|:\(id\))', '/os-fixed-ips/{fixed_ip}'),
    (r'/os-fping/(' + UUID4 + '|:\(id\))', '/os-fping/{instance_id}'),
    (r'/os-floating-ip-dns/(:domain_id|:\(id\))', '/os-floating-ip-dns/{domain}'),
    (r'/os-floating-ip-dns/([^/]+)/entries/\S+', '/os-floating-ip-dns/\g<1>/entries/{name}'),

    (r'/os-instance_usage_audit_log/[^/]+', '/os-instance_usage_audit_log/{before_timestamp}'),
    (r'/os-security-group-default-rules/(' + UUID4 + '|:\(id\))', '/os-security-group-default-rules/{security_group_default_rule_id}'),
    (r'/os-services/:\(id\)', '/os-services/{service_id}'),
    (r'/os-snapshots/(' + UUID4 + '|:\(id\))', '/os-snapshots/{snapshot_id}'),
    (r'/ips/(\S+|:\(id\))', '/ips/{network_label}'),
    (r'/os-quota-class-sets/(\S+|:\(id\))', '/os-quota-class-sets/{class_id}'),
    (r'/metadata/(\S+|:\(id\))', '/metadata/{key}'),
    (r'/extensions/(\S+|:\(id\))', '/extensions/{alias}'),
    (r'/os-certificates/(\S+|:\(id\))', '/os-certificates/{certificate_id}'),
    (r'/os-assisted-volume-snapshots/:\(id\)', '/os-assisted-volume-snapshots/{snapshot_id}'),
    (r'/os-floating-ips/(' + UUID4 + '|:\(id\))', '/os-floating-ips/{floating_ip_id}'),
    (r'/os-keypairs/[^/]+', '/os-keypairs/{keypair_name}'),
    (r'/os-instance-actions/[^/]+', '/os-instance-actions/{request_id}'),
    (r'/os-hosts/[^/]+', '/os-hosts/{host_name}'),
    (r'/os-interface/(' + UUID4 + '|:\(id\))', '/os-interface/{port_id}'),
    (r'/os-security-group-rules/(' + UUID4 + '|:\(id\))', '/os-security-group-rules/{security_group_rule_id}'),
    (r'/os-volume_attachments/(' + UUID4+ '|:\(id\))', '/os-volume_attachments/{attachment_id}'),
    (r'/flavors/(' + UUID4 + '|:flavor_id|:\(id\))', '/flavors/{flavor_id}'),
    (r'/flavors/[0-9]{7,}', '/flavors/{flavor_id}'),
    (r'/images/([0-9a-z]{7,8}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12,}(-[0-9a-z]+)?|:\(id\))', '/images/{image_id}'),
    (r'/os-quota-sets/([a-f0-9]{32}|:\(id\))', '/os-quota-sets/{tenant_id}'),
    (r'/os-simple-tenant-usage/([a-f0-9]{32}|:\(id\))', '/os-simple-tenant-usage/{tenant_id}'),
    (r'/os-server-groups/(' + UUID4 + '|:\(id\))', '/os-server-groups/{server_group_id}'),
    (r'/os-security-groups/(' + UUID4 + '|:\(id\))', '/os-security-groups/{security_group_id}'),
    (r'/os-hypervisors/.*/', '/os-hypervisors/{hypervisor_id}/'),
    (r'/os-hypervisors/(1|'+UUID4+'|:\(id\))', '/os-hypervisors/{hypervisor_id}'),
    (r'/os-tenant-networks/(' + UUID4 + '|:\(id\))', '/os-tenant-networks/{network_id}'),
    (r'/os-agents/([0-9]{1,8}|:\(id\))', '/os-agents/{agent_build_id}'),
    (r'/os-aggregates/([0-9]{1,8}|:\(id\))', '/os-aggregates/{aggregate_id}'),
    (r'/os-networks/(' + UUID4 + '|:\(id\))', '/os-networks/{network_id}'),
    (r'/os-extra_specs/([a-z0-9\-_]+|:\(id\))', '/os-extra_specs/{flavor_extra_spec_key}'),

    (r'/ports/' + UUID4, '/ports/{port_id}'),
    (r'/networks/' + UUID4, '/networks/{network_id}'),
    (r'/routers/' + UUID4, '/routers/{router_id}'),
    (r'/subnets/' + UUID4, '/subnets/{subnet_id}'),
    (r'/security-groups/' + UUID4, '/security-groups/{security_group_id}'),
    (r'/security-group-rules/' + UUID4, '/security-group-rules/{security-group-rules-id}'),
    (r'/floatingips/' + UUID4, '/floatingips/{floatingip_id}'),
    (r'/metering-labels/' + UUID4, '/metering-labels/{metering-label-id}'),
    (r'/metering-label-rules/' + UUID4, '/metering-label-rules/{metering-label-rule-id}'),
    (r'/agents/' + UUID4, '/agents/{agent_id}'),
    (r'/l3-routers/' + UUID4, '/l3-routers/{router_id}'),
    (r'/dhcp-networks/' + UUID4, '/dhcp-networks/{dhcp_networks_id}'),
    (r'/subnetpools/' + UUID4, '/subnetpools/{subnetpool_id}'),
    (r'/quotas/[a-f0-9]{32}', '/quotas/{tenant_id}'),

    (r'\?.*$', ''),                            # Remove query string
    (r'/(v\d+(\.\d+)?)/[a-f0-9]{32}', r'/\1/{project_id}'),
    (r'/{project_id:\[0-9a-f\\-]\+}/', r'/{project_id}/'),
    (r'tempest-[^/]+', 'resource_name'),
    (r'/Test[^?/&]+', '/resource_name'),
]

REPLACEMENTS_DICT = collections.OrderedDict(
    [(re.compile(regex), repl) for regex, repl in REPLACEMENTS_LIST]
)
