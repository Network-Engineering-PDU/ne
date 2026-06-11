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
            print('>>> Inputs PDU API - STARTED')
            response = requests.get(f'{BASE_URL_PDU}/inputs/', verify=False)
            if response.status_code == 200:
                """
                inputs response example:
                    [
                        {
                            "line_id": 1,
                            “low_limit”: 0.5,
                            “high_limit”: 12.5
                        },
                        {
                            "line_id": 2,
                            “low_limit”: 0.5,
                            “high_limit”: 12.5
                        },
                    ]
                """
                for elem in response.json():
                    input_obj, created = Input.objects.get_or_create(line_id=elem['line_id'])
                    if created:
                        input_obj.low_limit = float(elem['low_limit'])
                        input_obj.high_limit = float(elem['high_limit'])
                        input_obj.save()
                    print(f'>>> {input_obj.__str__()} {"created" if created else "updated"}!')

                print(f'>>> Inputs PDU API - COMPLETED ({len(response.json())} inputs)')

            print('>>> Outputs PDU API - STARTED')
            response = requests.get(f'{BASE_URL_PDU}/outputs/', verify=False)
            if response.status_code == 200:
                """
                inputs response example:
                    [
                        {
                            "line_id": 1,
                            "name": "Output 1",
                            "socket_type": "IEC 320 C13",
                            "low_limit": 0.0,
                            "high_limit": 3.0,
                        },
                        {
                            "line_id": 2,
                            "name": "Output 2",
                            "socket_type": "IEC 320 C13",
                            "low_limit": 0.0,
                            "high_limit": 3.0,
                        },
                    ]
                """
                for elem in response.json():
                    output_obj, created = Output.objects.get_or_create(line_id=elem['line_id'])
                    if created:
                        output_obj.name = elem['name']
                        output_obj.socket_type = elem['socket_type']
                        output_obj.low_limit = float(elem['low_limit'])
                        output_obj.high_limit = float(elem['high_limit'])
                        output_obj.save()
                    print(f'>>> {output_obj.__str__()} {"created" if created else "updated"}!')

                print(f'>>> Outputs PDU API - COMPLETED ({len(response.json())} inputs)')

            # Run Server
            call_command('runserver', BASE_URL_DJANGO.split('//')[1])

        except Exception as ex:
            print(f'Error {ex.__str__()}')
