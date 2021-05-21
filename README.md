# Overview

InfluxDB is an open-source, distributed, time series database.

## Description

InfluxData platform is the leading modern time series platform, built for metrics and events. 

The InfluxDB 2.0 platform consolidates InfluxDB, Chronograf, and Kapacitor from the InfluxData 1.x platform into a single packaged solution, with added features and flexibility:

    InfluxDB OSS 2.0: open source platform solution in a single binary
    InfluxDB Cloud (commercial offering): hosted cloud solution
    Telegraf: collect data

InfluxDB Enterprise 2.0 is in development. The initial release of v2.0 was on Nov'20.

## Usage

### Usage with Telegraf

Deploy the telegraf charm, and the required InfluxDB charm with the following:

    juju deploy telegraf
    juju deploy cs:~influxdb-charmers/influxdb

Add the relation between the two charms:

    juju add-relation influxdb telegraf

### Usage with Grafana

At the time of this charm release, Grafana's influxdb v2 datasource, using Flux
as the query language, is in beta. This charm exposes the required relation data
with Grafana but further testing is required.

Deploy the Grafana charm, and the required InfluxDB charm with the following:

    juju deploy grafana
    juju deploy influxdb2

Add the relation between the two charms:

    juju add-relation influxdb2:grafana-source grafana:grafana-source

The relationship will automatically register the InfluxDB instance as a
data source in Grafana.

However, you still need to create an InfluxDB database and populate the
Grafana data source page with its details. Once you have created an
InfluxDB database, visit the Grafana /datasources page, choose your
InfluxDB juju generated data source, and edit the database settings
accordingly.

# Authentication

The charm will create an "admin" account at install time with a hardcoded
password. The password can be manually changed from the UI, though.

All other authentication management must be done manually, including
to allow a related grafana access to use an InfluxDB data source.

## Roadmap

* Add support for Telegraf output plugin (telegraf to write metrics in influxdb2)
* Make authentication configurable via Juju (right now, the admin credentials are
hardcoded at deployment time)
* Add action to generate a new admin password, and retrieve the current admin password
* Add action to generate a new token, and delete old ones
* Scale Out: support a cluster of multiple containers running on different
nodes.
* Use an ingress service to avoid the cluster IP address from changing on every
k8s cluster restart (when testing in microk8s) or charm upgrade.

## Contribute

### Developing

Create and activate a virtualenv,
and install the development requirements,

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements-dev

### Testing

Just run `run_tests`:

    ./run_tests
