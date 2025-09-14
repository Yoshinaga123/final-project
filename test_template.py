#!/usr/bin/env python3
"""
テンプレートレンダリングのテスト
"""

from app import create_app
from flask import render_template

app = create_app('testing')

def test_template_rendering():
    with app.test_request_context():
        result = render_template('index.html')
    assert '<html' in result.lower()

if __name__ == "__main__":
    test_template_rendering()
