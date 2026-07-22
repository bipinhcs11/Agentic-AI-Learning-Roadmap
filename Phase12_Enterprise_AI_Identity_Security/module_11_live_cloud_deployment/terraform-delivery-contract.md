# Terraform Delivery Contract

Every Module 11 provider implementation must meet this contract before it is
described as deployable.

## Required layout

```text
<provider>/
├── README.md
├── versions.tf
├── providers.tf
├── variables.tf
├── main.tf
├── outputs.tf
├── terraform.tfvars.example
├── policies/
├── tests/
└── scripts/
    ├── smoke-test.sh
    └── verify-destroy.sh
```

Real `.tfvars`, Terraform state, plans, credentials, evidence, and crash logs
must remain ignored.

## Infrastructure requirements

- Pin Terraform and provider version ranges and commit the dependency lockfile.
- Use one remote encrypted state location per cloud environment.
- Require a unique fictional environment name and common ownership/cost labels.
- Make region, retention, capacity, and budget explicit variables.
- Validate names, allowed regions, and safe development capacity ranges.
- Mark sensitive inputs and outputs; never output a secret value.
- Prefer private networking and workload identity over IP allow-lists or keys.
- Separate deployer, runtime, migration, and observability permissions.
- Reference container images by immutable digest for reviewed deployments.
- Expose only the minimum health and gateway routes.

## Pipeline gates

The pull-request workflow should run read-only checks:

```text
terraform fmt -check
terraform init -backend=false
terraform validate
IaC security scan
policy tests
terraform test, where supported
```

Planning uses a keyless, read-oriented identity. Applying requires protected
environment approval and a short-lived deployment identity. Destruction uses
the same approval boundary and always runs the post-destroy inventory check.

## Definition of done

- A fresh environment can be created from documented prerequisites.
- A reviewed plan contains no unexpected public or privileged resources.
- All shared security acceptance tests pass against the live endpoint.
- Logs preserve `audit_id` without recording raw tokens or fictional payloads.
- Revocation is effective before the task JWT expires.
- Teardown succeeds after both a healthy deployment and a partial failure.
- Provider inventory confirms no billable lab resources remain.
