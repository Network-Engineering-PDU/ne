import requests
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand

from app.models import Input, Output
from ne.settings import (
    SUPERUSER_USERNAME, SUPERUSER_EMAIL, SUPERUSER_FIRST_NAME,
    SUPERUSER_LAST_NAME, SUPERUSER_PASSWORD, BASE_URL_DJANGO, BASE_URL_PDU
)


class Command(BaseCommand):

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        try:

            # Migrate
            call_command('migrate')

            # SuperUser
            print(">>> Superuser - STARTED")
            superuser, created = User.objects.get_or_create(username=SUPERUSER_USERNAME)
            superuser.email = SUPERUSER_EMAIL
            superuser.first_name = SUPERUSER_FIRST_NAME
            superuser.last_name = SUPERUSER_LAST_NAME
            superuser.is_staff = True
            superuser.is_superuser = True
            superuser.set_password(SUPERUSER_PASSWORD)
            superuser.save()
            print(f'>>> SuperUser {superuser} has been {"created" if created else "updated"}!')

            # Get Inputs and Outputs to populate tables
            def fetch_pdu_api(path):
                try:
                    response = requests.get(f'{BASE_URL_PDU}/{path}', verify=False, timeout=5)
                    if response.status_code == 200:
                        return response.json()
                    print(f'>>> PDU API {path} returned {response.status_code}')
                except requests.exceptions.RequestException as ex:
                    print(f'>>> PDU API {path} request failed: {ex}')
                return None

            print('>>> Inputs PDU API - STARTED')
            inputs_data = fetch_pdu_api('inputs/')
            if inputs_data is not None:
                for elem in inputs_data:
                    input_obj, created = Input.objects.get_or_create(line_id=elem['line_id'])
                    if created:
                        input_obj.low_limit = float(elem['low_limit'])
                        input_obj.high_limit = float(elem['high_limit'])
                        input_obj.save()
                    print(f'>>> {input_obj.__str__()} {"created" if created else "updated"}!')
                print(f'>>> Inputs PDU API - COMPLETED ({len(inputs_data)} inputs)')
            else:
                print('>>> Inputs PDU API - SKIPPED (unavailable)')

            print('>>> Outputs PDU API - STARTED')
            outputs_data = fetch_pdu_api('outputs/')
            if outputs_data is not None:
                for elem in outputs_data:
                    output_obj, created = Output.objects.get_or_create(line_id=elem['line_id'])
                    if created:
                        output_obj.name = elem['name']
                        output_obj.socket_type = elem['socket_type']
                        output_obj.low_limit = float(elem['low_limit'])
                        output_obj.high_limit = float(elem['high_limit'])
                        output_obj.save()
                    print(f'>>> {output_obj.__str__()} {"created" if created else "updated"}!')
                print(f'>>> Outputs PDU API - COMPLETED ({len(outputs_data)} outputs)')
            else:
                print('>>> Outputs PDU API - SKIPPED (unavailable)')

            # Run Server
            call_command('runserver', BASE_URL_DJANGO.split('//')[1], use_reloader=False)

        except Exception as ex:
            print(f'Error {ex.__str__()}')
