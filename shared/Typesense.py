import os
import json
import datetime
import http.client

from django.db import connection

class Typesense:
    def _date_to_year(self, dateString):
        date = datetime.datetime.strptime(str(dateString), '%Y-%m-%d') if dateString else None
        epoch = date.timestamp() if date else 0
        year = date.year if date else 0

        return (year, int(epoch))

    def _datetime_to_year(self, dateString):
        date = datetime.datetime.strptime(str(dateString), '%Y-%m-%d %H:%M:%S.%f') if dateString else None
        epoch = date.timestamp() if date else 0
        year = date.year if date else 0

        return (year, int(epoch))

    def create_collection(self):
        schema = {
            "name": "companies",
            "fields": [
                { "name": "id", "type": "int32" },
                { "name": "vil", "type": "int32" },
                { "name": "uid", "type": "string" },
                { "name": "logo", "type": "string" },
                { "name": "type", "type": "string" },
                { "name": "about", "type": "string" },
                { "name": "company_id", "type": "int32" },
                { "name": "name", "type": "string", "sort": True },
                { "name": "cities", "type": "string[]", "facet": True },
                { "name": "regions", "type": "string[]", "facet": True },
                { "name": "countries", "type": "string[]", "facet": True },
                { "name": "sectors", "type": "string[]", "facet": True },
                { "name": "founding_date", "type": "int32", "facet": True },
                { "name": "latest_assessment", "type": "int32", "facet": True },
            ],
            "default_sorting_field": "name"
        }

        return schema


    def seed(self, action):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                   SELECT
                        VC.id as company_id,
                        VC.uid as uid,
                        VC.name as name,
                        VC.about as about,
                        GL.value as vil,
                        VLOC.regions as regions,
                        VC.founded_date as founding_date,
                        VC.logo as logo,
                        VLOC.countries as countries,
                        VS.sectors as sectors,
                        VC.type as type,
                        GA.updated_at as latest_assessment,
                        VLOC.cities as cities
                    FROM viral_company as VC
                    JOIN (
                        SELECT DISTINCT ON (evaluated) id, evaluated, level_id, updated_at
                        FROM grid_assessment
                        ORDER BY evaluated, updated_at DESC
                    ) as GA on GA.evaluated = VC.id
                    JOIN grid_level as GL on GL.id = GA.level_id
                    JOIN (
                        SELECT
                            vcl.company_id as company_id,
                            STRING_AGG(vl.region, ',') as regions,
                            STRING_AGG(vl.country, ',') as countries,
                            STRING_AGG(vl.city, ',') as cities
                        FROM viral_company_locations as vcl
                        JOIN viral_location as vl on vl.id = vcl.location_id
                        GROUP BY vcl.company_id, vl.region, vl.country
                    ) VLOC on VLOC.company_id = VC.id
                    JOIN (
                        SELECT
                            vcs.company_id as company_id,
                            STRING_AGG(vs.name, ',') as sectors
                        FROM viral_company_sectors as vcs
                        JOIN viral_sector as vs on vs.id = vcs.sector_id
                        GROUP BY vcs.company_id
                    ) as VS on VS.company_id = VC.id
                    WHERE type = 0
                    GROUP BY VC.id, VC.uid, GL.value, VC.name, GA.updated_at, VS.sectors, VLOC.regions, VLOC,countries, VLOC.cities
                    ORDER BY latest_assessment DESC;
                """
            )

            entrpreneurs = cursor.fetchall()

            payload = []
            for row in entrpreneurs:
                company_type = row[10]
                if company_type == 0:
                    company_type = 'entreprenuer'
                elif company_type == 1:
                    company_type = 'supporter'
                else:
                    company_type = 'UNKNOWN'

                cities = row[12].split(',') if row[12] else []
                sectors = row[9].split(',') if row[9] else []
                regions = row[5].split(',') if row[5] else []
                countries = row[8].split(',') if row[8] else []
                (founding_year, founding_epoch) = self._date_to_year(row[6] if row[6] else None)
                (latest_assessment_year, latest_assessment_epoch) = self._datetime_to_year(row[11] if row[11] else None)

                payload.append(
                    json.dumps(
                        {
                            'id': str(row[0]),
                            'company_id': row[0],
                            'uid': row[1],
                            'name': row[2],
                            'about': row[3] if row[3] else '',
                            'logo': row[7] if row[7] else '',
                            'vil': row[4] if row[4] else 0,
                            'founding_date': founding_year,
                            'sectors': sectors,
                            'cities': cities,
                            'countries': countries,
                            'regions': regions,
                            'type': company_type,
                            'latest_assessment': latest_assessment_epoch,
                        }
                    )
                )

            cursor.execute(
                """
                    SELECT
                        VC.id as company_id,

                        VC.uid as uid,
                        VC.name as name,
                        VC.about as about,
                        VC.logo as logo,
                        VC.type as type,
                        VLOC.countries as counties,
                        VLOC.regions as regions,
                        VLOC.cities as cities,
                        VS.sectors as sectors
                                        FROM viral_company AS VC
                                        LEFT JOIN (
                        SELECT
                            vcl.company_id as company_id,
                            STRING_AGG(vl.region, ',') as regions,
                            STRING_AGG(vl.country, ',') as countries,
                            STRING_AGG(vl.city, ',') as cities
                        FROM viral_company_locations as vcl
                        JOIN viral_location as vl on vl.id = vcl.location_id
                        GROUP BY vcl.company_id, vl.region, vl.country
                                        ) VLOC on VLOC.company_id = VC.id
                                        LEFT JOIN (
                        SELECT
                            vcs.company_id as company_id,
                            STRING_AGG(vs.name, ',') as sectors
                        FROM viral_company_sectors as vcs
                        JOIN viral_sector as vs on vs.id = vcs.sector_id
                        GROUP BY vcs.company_id
                    ) as VS on VS.company_id = VC.id
                    WHERE type = 1
                    GROUP BY VC.id, VC.uid, VC.name, VLOC.regions, VLOC,countries, VLOC.cities, VS.sectors;
                """
            )

            supporters = cursor.fetchall()
            for row in supporters:
                cities = row[8].split(',') if row[8] else []
                sectors = row[9].split(',') if row[9] else []
                regions = row[7].split(',') if row[7] else []
                countries = row[6].split(',') if row[6] else []

                payload.append(
                    json.dumps(
                        {
                            'id': str(row[0]),
                            'company_id': row[0],
                            'uid': row[1],
                            'name': row[2],
                            'about': row[3] if row[3] else '',
                            'logo': row[4] if row[4] else '',
                            'vil': 0,
                            'founding_date': 0,
                            'sectors': sectors,
                            'cities': cities,
                            'regions': regions,
                            'countries': countries,
                            'type': 'supporter',
                            'latest_assessment': 0,
                        }
                    ),
                )

            payload = '\n'.join(payload)
            conn = http.client.HTTPSConnection('f0rocst9z8dib4m2p-1.a1.typesense.net')
            headers = {
                'X-TYPESENSE-API-KEY': os.getenv('TYPESENSE_ADMIN_API_KEY'),
                'Host': 'f0rocst9z8dib4m2p-1.a1.typesense.net',
                'Connection': 'keep-alive',
            }
            endpoint = '/collections/companies/documents/import?action=upsert' if action == "update" else '/collections/companies/documents/import'
            conn.request(
                'POST',
                endpoint,
                payload.encode('utf-8'),
                headers,
            )
            res = conn.getresponse()
            data = res.read()

            return data
