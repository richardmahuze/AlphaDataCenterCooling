# -*- coding: utf-8 -*-
"""
This module implements the REST API used to interact with the test case.
The API is implemented using the ``flask`` package.

"""

# GENERAL PACKAGE IMPORT
# ----------------------
from flask import Flask, make_response
from flask_restful import Resource, Api, reqparse
import flask_restful
from flask_cors import CORS
import six
from utils import MLP
# ----------------------


# GENERAL HTTP RESPONSE
# ----------------------
def construct(status, message, payload):
    response = {'status': status,
                'message': message,
                'payload': payload}
    return make_response(response, status)
# ----------------------


# TEST CASE IMPORT
# ----------------
# from testcase_datacenter import TestCase
from testcase import TestCase
# ----------------

# FLASK REQUIREMENTS
# ------------------


class CustomArgument(reqparse.Argument):

    def handle_validation_error(self, error, bundle_errors):
        '''Customizes inherited class with general HTTP response ``construct``.

        Called when an error is raised while parsing. Aborts the request
        with a 400 status and an error message

        :param error: the error that was raised
        :param bundle_errors: do not abort when first error occurs, return a
            dict with the name of the argument and the error message to be
            bundled

        '''

        error_str = six.text_type(error)
        msg = 'Bad input for parameter {}. '.format(self.name) + error_str
        flask_restful.abort(construct(400, msg, None))

app = Flask(__name__)
cors = CORS(app, resources={r"*": {"origins": "*"}})
api = Api(app)
# ------------------

# INSTANTIATE TEST CASE
# ---------------------
case = TestCase()
# ---------------------

# DEFINE ARGUMENT PARSERS
# -----------------------
# ``step`` interface
parser_step = reqparse.RequestParser(argument_class=CustomArgument)
parser_step.add_argument('step', required=True)

# ``initialize`` interface
parser_initialize = reqparse.RequestParser(argument_class=CustomArgument)
parser_initialize.add_argument('start_time', required=True)
parser_initialize.add_argument('end_time', required=False)
# ``advance`` interface
parser_advance = reqparse.RequestParser(argument_class=CustomArgument)
for key in case.u.keys():
    if key != 'time':
        parser_advance.add_argument(key, type=float)

# ``results`` interface
results_var = reqparse.RequestParser(argument_class=CustomArgument)
results_var.add_argument('point_names', type=list, action='append', required=True)
results_var.add_argument('start_time', required=True)
results_var.add_argument('final_time', required=True)

# -----------------------


# DEFINE REST REQUESTS
# --------------------
class Advance(Resource):
    '''Interface to advance the test case simulation.'''

    def post(self):
        '''POST request with input data to advance the simulation one step
        and receive current measurements.'''
        u = parser_advance.parse_args(strict=True)
        status, message, payload = case.advance(u)
        return construct(status, message, payload)


class Initialize(Resource):
    '''Interface to initialize the test case simulation.'''

    def put(self):
        '''PUT request to initialize the test.'''
        args = parser_initialize.parse_args()
        start_time = args['start_time']
        end_time= args.get('end_time', None)
        if end_time:
            status, message, payload = case.initialize(start_time,end_time)
        else:
            status, message, payload = case.initialize(start_time)
        return construct(status, message, payload)


class Step(Resource):
    '''Interface to test case simulation step size.'''

    def get(self):
        '''GET request to receive current simulation step in seconds.'''
        status, message, payload = case.get_step()
        return construct(status, message, payload)

    def put(self):
        '''PUT request to set simulation step in seconds.'''
        args = parser_step.parse_args()
        step = args['step']
        status, message, payload = case.set_step(step)
        return construct(status, message, payload)


class Inputs(Resource):
    '''Interface to test case inputs.'''

    def get(self):
        '''GET request to receive list of available inputs.'''
        status, message, payload = case.get_inputs()
        return construct(status, message, payload)


class Measurements(Resource):
    '''Interface to test case measurements.'''

    def get(self):
        '''GET request to receive list of available measurements.'''
        status, message, payload = case.get_measurements()
        return construct(status, message, payload)



class Results(Resource):
    '''Interface to test case result data.'''

    def put(self):
        '''PUT request to receive measurement data.'''
        args = results_var.parse_args(strict=True)
        point_names = []
        for point_name in args['point_names']:
            point_names.append(''.join(point_name))
        start_time = args['start_time']
        final_time = args['final_time']
        status, message, payload = case.get_results(point_names, start_time, final_time)
        return construct(status, message, payload)




class Name(Resource):
    '''Interface to test case name.'''

    def get(self):
        '''GET request to receive test case name.'''
        status, message, payload = case.get_name()
        return construct(status, message, payload)

class Version(Resource):
    '''Interface to BOPTEST version.'''

    def get(self):
        '''GET request to receive BOPTEST version.'''
        status, message, payload = case.get_version()
        return construct(status, message, payload)

# --------------------

# ADD REQUESTS TO API WITH URL EXTENSION
# --------------------------------------
api.add_resource(Advance, '/advance')
api.add_resource(Initialize, '/initialize')
api.add_resource(Step, '/step')
api.add_resource(Inputs, '/inputs')
api.add_resource(Measurements, '/measurements')
api.add_resource(Results, '/results')
api.add_resource(Name, '/name')
api.add_resource(Version, '/version')
# --------------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0')