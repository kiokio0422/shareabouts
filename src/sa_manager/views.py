from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse
import json
import re
import requests

API_ROOT = '/api/v1/'

def index_view(request):
    return render(request, "manager/index.html")


def places_view(request):
    places_uri = request.build_absolute_uri(API_ROOT + 'places/')

    # TODO Is this the best way to get the API data?
    response = requests.get(places_uri)

    places = json.loads(response.text)
    return render(request, "manager/places.html", {'places': places})


def process_new_attr(data, num):
    meta_key = '_new_key{0}'.format(num)
    meta_val = '_new_val{0}'.format(num)

    new_key = data.get(meta_key, '').strip()
    new_val = data.get(meta_val, '')

    if meta_key in data:
        del data[meta_key]
    if meta_val in data:
        del data[meta_val]

    if new_key and new_val:
        data[new_key] = new_val

    return new_key, new_val


def process_place_data(data):
    """
    Prepare place data to be sent to the service for creating or updating.
    """
    # Pull out data we don't want to send to the server
    if 'csrfmiddlewaretoken' in data:
        del data['csrfmiddlewaretoken']
    if 'action' in data:
        del data['action']

    # Fix the location to be something the server will understand
    location = {
      'lat': data.get('lat'),
      'lng': data.get('lng')
    }
    del data['lat']
    del data['lng']
    data['location'] = location

    # Fix the visibility to be either true or false (boolean)
    data['visible'] = ('visible' in data)

    for key, value in data.items():
        # Get rid of any empty data
        if value == '':
            del data[key]
            continue

        # Add any new keys to the data dictionary
        if key.startswith('_new_key'):
            num = key[8:]
            process_new_attr(data, num)
            continue

    return data


def new_place_view(request):
    places_uri = request.build_absolute_uri(API_ROOT + 'places/')

    def initial(request):
        return render(request, "manager/place.html")

    def create(request):
        # Make a copy of the POST data, since we can't edit the original.
        data = request.POST.dict()
        data = process_place_data(data)

        # Send the save request
        response = requests.post(places_uri, data=json.dumps(data),
            headers={'Content-type': 'application/json'})
        if response.status_code == 201:
            data = json.loads(response.text)
            place_id = data.get('id')

            messages.success(request, 'Successfully saved!')
            return redirect(reverse('manager_place_detail', args=[place_id]))

        else:
            messages.error(request, 'Error: ' + response.text)
            return redirect(request.get_full_path())


    if request.method == 'GET':
        return initial(request)
    elif request.method == 'POST':
        return create(request)
    else:
        # TODO 405 on other
        pass


def place_view(request, pk):
    place_uri = request.build_absolute_uri(API_ROOT + 'places/{0}/'.format(pk))

    def read(request, pk):
        # Retrieve the place data.
        response = requests.get(place_uri)
        place = json.loads(response.text)

        # Arrange the place data fields for display on the form
        data_fields = []
        special_fields = ('id', 'location', 'submitter_name', 'name', 'visible',
                          'created_datetime', 'updated_datetime', 'url',
                          'submissions')
        for key, value in place.items():
            if key not in special_fields:
                label = key.replace('_', ' ').title()
                data_fields.append((label, key, value))
        data_fields.sort()

        return render(request, "manager/place.html", {
            'place': place,
            'data_fields': data_fields
        })

    def update(request, pk):
        # Make a copy of the POST data, since we can't edit the original.
        data = request.POST.dict()
        data = process_place_data(data)

        # Send the save request
        response = requests.put(place_uri, data=json.dumps(data),
            headers={'Content-type': 'application/json'})

        if response.status_code == 200:
            messages.success(request, 'Successfully saved!')

        else:
            messages.error(request, 'Error: ' + response.text)

        return redirect(request.get_full_path())

    def delete(request, pk):
        # Send the delete request
        response = requests.delete(place_uri)

        if response.status_code == 204:
            messages.success(request, 'Successfully deleted!')
            return redirect(reverse('manager_place_list'))

        else:
            messages.error(request, 'Error: ' + response.text)
            return redirect(request.get_full_path())


    if request.method == 'GET':
        return read(request, pk)
    elif request.method == 'POST':
        if request.POST.get('action') == 'save':
            return update(request, pk)
        elif request.POST.get('action') == 'delete':
            return delete(request, pk)
        else:
            # TODO ???
            pass
    else:
        # TODO 405 on other
        pass

def place_submissions_view(request, pk):
    place_uri = request.build_absolute_uri(API_ROOT + 'places/{0}/'.format(pk))
    submissions_uri = lambda submission_type: request.build_absolute_uri(API_ROOT + 'places/{0}/{1}/'.format(pk, submission_type))

    def index():
        # Retrieve the place data.
        response = requests.get(place_uri)
        place = json.loads(response.text)

        submission_sets = place['submissions']
        for submission_set in submission_sets:
            stype = submission_set['type']
            response = requests.get(submissions_uri(stype))

            submission_set['label'] = submission_set['type'].replace('_', ' ').title()
            submission_set['submissions'] = json.loads(response.text)

            for submission in submission_set['submissions']:
                # Arrange the place data fields for display on the form
                data_fields = []
                special_fields = ('id', 'submitter_name', 'url',
                                  'created_datetime', 'updated_datetime')
                for key, value in submission.items():
                    if key not in special_fields:
                        label = key.replace('_', ' ').title()
                        data_fields.append((label, key, value))
                data_fields.sort()

                submission['data_fields'] = data_fields



        return render(request, "manager/place_submissions.html", {
            'place': place,
        })

    if request.method == 'GET':
        return index()
