"""Supafone-managed runtime adapter.

Managed browser and phone agents currently use the Ultravox data-message
transport, but retain a distinct provider id so the public fourteen-runtime
matrix can test and report the hosted path independently.
"""
from supafone_labs.runtime.adapters.ultravox import UltravoxAdapter


class SupafoneAdapter(UltravoxAdapter):
    provider_name = "supafone"
