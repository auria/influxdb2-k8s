# Overview

InfluxDB is an open-source, distributed, time series database.

## Description

InfluxData platform is the leading modern time series platform, built for metrics and events. 

The InfluxDB 2.0 platform consolidates InfluxDB, Chronograf, and Kapacitor from the InfluxData 1.x platform into a single packaged solution, with added features and flexibility:

    InfluxDB OSS 2.0: open source platform solution in a single binary
    InfluxDB Cloud (commercial offering): hosted cloud solution
    Telegraf: collect data

InfluxDB Enterprise 2.0 is in development.

## Usage

### Usage with Telegraf

Deploy the telegraf charm, and the required InfluxDB charm with the following:

    juju deploy telegraf
    juju deploy cs:~influxdb-charmers/influxdb

Add the relation between the two charms:

    juju add-relation influxdb telegraf

### Usage with Grafana

Deploy the Grafana charm, and the required InfluxDB charm with the following:

    juju deploy grafana
    juju deploy cs:~influxdb-charmers/influxdb

Add the relation between the two charms:

    juju add-relation influxdb:grafana-source grafana:grafana-source

The relationship will automatically register the InfluxDB instance as a
data source in Grafana.

However, you still need to create an InfluxDB database and populate the
Grafana data source page with its details. Once you have created an
InfluxDB database, visit the Grafana /datasources page, choose your
InfluxDB juju generated data source, and edit the database settings
accordingly.

# Authentication

To enable authentication, add "http.auth-enabled=true" to
extra_configs, e.g., if there are no other options set:

    juju config influxdb extra_configs="- http.auth-enabled=true"

Whether authentication is enabled or not, the charm will create an
"admin" account at install time and store the credentials in
`/root/.influx-auth`.  If the application is related to cs:nrpe, it
will create a "nagios" account and store the credentials in
`/var/lib/nagios/.influx-auth`, as the Nagios check expects.
Due to the way the check works, this is also an admin account.

All other authentication management must be done manually, including
to allow a related grafana access to use an InfluxDB data source.

## Roadmap

* Scale Out Usage

This charm implements the logic of the non-k8s version available at 
An earlier version of this charm contained .deb and .tar.gz files
for InfluxDB and Python dependencies. They have been removed from
the git repository, so you will need to ensure you are using an up
to date clone of the codebase before making any changes.

...

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
