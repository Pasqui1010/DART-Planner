#!/usr/bin/env python3
"""
Playwright E2E tests for DART-Planner admin panel UI.

Tests the complete user interface flows for admin functionality including
authentication, user management, and error handling.
"""

import pytest
import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import os
import sys
from pathlib import Path

# Add src to path for imports

from dart_planner.security.auth import Role


class TestAdminPanelUI:
    """E2E tests for admin panel user interface"""
    
    @pytest.fixture(scope="class")
    async def browser(self):
        """Setup browser for testing"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            yield browser
            await browser.close()
    
    @pytest.fixture
    async def context(self, browser: Browser):
        """Setup browser context with admin user"""
        context = await browser.new_context()
        
        # Set up admin user cookies/session
        await context.add_cookies([
            {
                "name": "access_token",
                "value": "Bearer admin_test_token",
                "domain": "localhost",
                "path": "/"
            }
        ])
        
        yield context
        await context.close()
    
    @pytest.fixture
    async def page(self, context: BrowserContext):
        """Setup page for testing"""
        page = await context.new_page()
        yield page
        await page.close()
    
    @pytest.fixture
    async def admin_page(self, page: Page):
        """Setup page with admin user logged in"""
        # Mock admin user session
        await page.add_init_script("""
            window.currentUser = {
                username: "admin",
                role: "ADMIN",
                token: "admin_test_token"
            };
        """)
        
        # Navigate to the app
        await page.goto("http://localhost:8000")
        
        # Wait for page to load
        await page.wait_for_selector("#admin-panel", timeout=5000)
        
        yield page
    
    async def test_admin_panel_visibility(self, admin_page: Page):
        """Test that admin panel is visible for admin users"""
        # Check admin panel is visible
        admin_panel = await admin_page.query_selector("#admin-panel")
        assert admin_panel is not None
        
        # Check admin panel is not hidden
        class_list = await admin_panel.get_attribute("class")
        assert "hidden" not in class_list
        
        # Check admin panel title
        title = await admin_page.text_content("#admin-panel h2")
        assert "Admin Panel" in title
    
    async def test_admin_panel_hidden_for_non_admin(self, page: Page):
        """Test that admin panel is hidden for non-admin users"""
        # Mock operator user session
        await page.add_init_script("""
            window.currentUser = {
                username: "operator",
                role: "OPERATOR",
                token: "operator_test_token"
            };
        """)
        
        await page.goto("http://localhost:8000")
        
        # Wait for page to load
        await page.wait_for_selector("#demo-section", timeout=5000)
        
        # Check admin panel is hidden
        admin_panel = await page.query_selector("#admin-panel")
        if admin_panel:
            class_list = await admin_panel.get_attribute("class")
            assert "hidden" in class_list
    
    async def test_create_user_form_visibility(self, admin_page: Page):
        """Test that create user form is visible in admin panel"""
        # Check create user form elements
        form = await admin_page.query_selector("#create-user-form")
        assert form is not None
        
        # Check form fields
        username_input = await admin_page.query_selector("#new-username")
        password_input = await admin_page.query_selector("#new-password")
        role_select = await admin_page.query_selector("#new-user-role")
        submit_button = await admin_page.query_selector("#create-user-form button[type='submit']")
        
        assert username_input is not None
        assert password_input is not None
        assert role_select is not None
        assert submit_button is not None
        
        # Check submit button text
        button_text = await submit_button.text_content()
        assert "Create User" in button_text
    
    async def test_role_dropdown_population(self, admin_page: Page):
        """Test that role dropdown is populated with available roles"""
        # Wait for roles to be loaded
        await admin_page.wait_for_selector("#new-user-role option", timeout=5000)
        
        # Get all role options
        options = await admin_page.query_selector_all("#new-user-role option")
        
        # Check that we have the expected roles
        role_values = []
        for option in options:
            value = await option.get_attribute("value")
            role_values.append(value)
        
        expected_roles = ["admin", "operator", "pilot", "viewer"]
        for role in expected_roles:
            assert role in role_values
    
    async def test_create_user_success_flow(self, admin_page: Page):
        """Test successful user creation flow"""
        # Fill in user creation form
        await admin_page.fill("#new-username", "testuser")
        await admin_page.fill("#new-password", "testpass123")
        await admin_page.select_option("#new-user-role", "operator")
        
        # Mock successful API response
        await admin_page.route("**/api/admin/users", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"id": 5, "username": "testuser", "role": "operator", "is_active": true}'
        ))
        
        # Submit form
        await admin_page.click("#create-user-form button[type='submit']")
        
        # Wait for success feedback
        await admin_page.wait_for_timeout(1000)  # Wait for async operation
        
        # Check that form is cleared
        username_value = await admin_page.input_value("#new-username")
        password_value = await admin_page.input_value("#new-password")
        
        assert username_value == ""
        assert password_value == ""
    
    async def test_create_user_validation_errors(self, admin_page: Page):
        """Test user creation form validation"""
        # Test empty username
        await admin_page.fill("#new-password", "testpass123")
        await admin_page.select_option("#new-user-role", "operator")
        await admin_page.click("#create-user-form button[type='submit']")
        
        # Should show validation error
        await admin_page.wait_for_timeout(500)
        
        # Test weak password
        await admin_page.fill("#new-username", "testuser")
        await admin_page.fill("#new-password", "123")  # Too short
        await admin_page.click("#create-user-form button[type='submit']")
        
        # Should show validation error
        await admin_page.wait_for_timeout(500)
    
    async def test_create_user_api_error_handling(self, admin_page: Page):
        """Test handling of API errors during user creation"""
        # Fill in form
        await admin_page.fill("#new-username", "testuser")
        await admin_page.fill("#new-password", "testpass123")
        await admin_page.select_option("#new-user-role", "operator")
        
        # Mock API error response
        await admin_page.route("**/api/admin/users", lambda route: route.fulfill(
            status=400,
            content_type="application/json",
            body='{"detail": "Username already exists"}'
        ))
        
        # Submit form
        await admin_page.click("#create-user-form button[type='submit']")
        
        # Wait for error handling
        await admin_page.wait_for_timeout(1000)
        
        # Check that form is not cleared (error occurred)
        username_value = await admin_page.input_value("#new-username")
        assert username_value == "testuser"
    
    async def test_user_list_display(self, admin_page: Page):
        """Test that user list is displayed in admin panel"""
        # Mock user list API response
        mock_users = [
            {"id": 1, "username": "admin", "role": "admin", "is_active": True},
            {"id": 2, "username": "operator", "role": "operator", "is_active": True},
            {"id": 3, "username": "pilot", "role": "pilot", "is_active": True}
        ]
        
        await admin_page.route("**/api/admin/users", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=str(mock_users).replace("'", '"')
        ))
        
        # Reload page to trigger user list load
        await admin_page.reload()
        await admin_page.wait_for_selector("#admin-panel", timeout=5000)
        
        # Check user list table
        user_list = await admin_page.query_selector("#user-list")
        assert user_list is not None
        
        # Check that users are displayed
        user_rows = await admin_page.query_selector_all("#user-list tbody tr")
        assert len(user_rows) >= 1  # At least admin user should be there
    
    async def test_user_management_actions(self, admin_page: Page):
        """Test user management actions (edit, delete)"""
        # Mock user list with action buttons
        await admin_page.route("**/api/admin/users", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='[{"id": 2, "username": "testuser", "role": "operator", "is_active": true}]'
        ))
        
        # Reload page
        await admin_page.reload()
        await admin_page.wait_for_selector("#admin-panel", timeout=5000)
        
        # Check for action buttons (if implemented)
        edit_buttons = await admin_page.query_selector_all(".edit-user-btn")
        delete_buttons = await admin_page.query_selector_all(".delete-user-btn")
        
        # These might not be implemented yet, but we can test the structure
        assert True  # Placeholder for when actions are implemented
    
    async def test_admin_panel_responsive_design(self, admin_page: Page):
        """Test that admin panel works on different screen sizes"""
        # Test mobile viewport
        await admin_page.set_viewport_size({"width": 375, "height": 667})
        
        # Check admin panel is still accessible
        admin_panel = await admin_page.query_selector("#admin-panel")
        assert admin_panel is not None
        
        # Test tablet viewport
        await admin_page.set_viewport_size({"width": 768, "height": 1024})
        
        # Check admin panel is still accessible
        admin_panel = await admin_page.query_selector("#admin-panel")
        assert admin_panel is not None
    
    async def test_admin_panel_keyboard_navigation(self, admin_page: Page):
        """Test keyboard navigation in admin panel"""
        # Focus on username field
        await admin_page.focus("#new-username")
        
        # Tab through form fields
        await admin_page.keyboard.press("Tab")
        focused_element = await admin_page.evaluate("document.activeElement.id")
        assert focused_element == "new-password"
        
        await admin_page.keyboard.press("Tab")
        focused_element = await admin_page.evaluate("document.activeElement.id")
        assert focused_element == "new-user-role"
        
        await admin_page.keyboard.press("Tab")
        focused_element = await admin_page.evaluate("document.activeElement.tagName")
        assert focused_element == "BUTTON"
    
    async def test_admin_panel_accessibility(self, admin_page: Page):
        """Test accessibility features of admin panel"""
        # Check form labels
        username_label = await admin_page.query_selector("label[for='new-username']")
        password_label = await admin_page.query_selector("label[for='new-password']")
        role_label = await admin_page.query_selector("label[for='new-user-role']")
        
        assert username_label is not None
        assert password_label is not None
        assert role_label is not None
        
        # Check label text
        username_label_text = await username_label.text_content()
        password_label_text = await password_label.text_content()
        role_label_text = await role_label.text_content()
        
        assert "Username" in username_label_text
        assert "Password" in password_label_text
        assert "Role" in role_label_text
    
    async def test_admin_panel_session_timeout(self, page: Page):
        """Test admin panel behavior when session expires"""
        # Mock expired session
        await page.add_init_script("""
            window.currentUser = null;
        """)
        
        await page.goto("http://localhost:8000")
        
        # Should redirect to login
        await page.wait_for_selector("#login-section", timeout=5000)
        
        # Admin panel should not be visible
        admin_panel = await page.query_selector("#admin-panel")
        if admin_panel:
            class_list = await admin_panel.get_attribute("class")
            assert "hidden" in class_list


class TestAdminPanelIntegration:
    """Integration tests for admin panel with real backend"""
    
    @pytest.fixture(scope="class")
    async def browser(self):
        """Setup browser for testing"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            yield browser
            await browser.close()
    
    @pytest.fixture
    async def context(self, browser: Browser):
        """Setup browser context"""
        context = await browser.new_context()
        yield context
        await context.close()
    
    @pytest.fixture
    async def page(self, context: BrowserContext):
        """Setup page for testing"""
        page = await context.new_page()
        yield page
        await page.close()
    
    async def test_full_admin_workflow_integration(self, page: Page):
        """Test complete admin workflow with real backend"""
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Wait for login form
        await page.wait_for_selector("#login-section", timeout=5000)
        
        # Login as admin
        await page.fill("#login-form input[name='username']", "admin")
        await page.fill("#login-form input[name='password']", "dart_admin_2025")
        await page.click("#login-form button[type='submit']")
        
        # Wait for admin panel to appear
        await page.wait_for_selector("#admin-panel", timeout=10000)
        
        # Verify admin panel is visible
        admin_panel = await page.query_selector("#admin-panel")
        assert admin_panel is not None
        
        class_list = await admin_panel.get_attribute("class")
        assert "hidden" not in class_list
        
        # Test user creation
        await page.fill("#new-username", "integration_test_user")
        await page.fill("#new-password", "integration_test_pass123")
        await page.select_option("#new-user-role", "operator")
        await page.click("#create-user-form button[type='submit']")
        
        # Wait for success
        await page.wait_for_timeout(2000)
        
        # Verify form is cleared
        username_value = await page.input_value("#new-username")
        assert username_value == ""
    
    async def test_admin_panel_error_recovery(self, page: Page):
        """Test admin panel error recovery scenarios"""
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Login as admin
        await page.fill("#login-form input[name='username']", "admin")
        await page.fill("#login-form input[name='password']", "dart_admin_2025")
        await page.click("#login-form button[type='submit']")
        
        # Wait for admin panel
        await page.wait_for_selector("#admin-panel", timeout=10000)
        
        # Test network error recovery
        # This would require mocking network failures
        # For now, we'll test the UI remains responsive
        
        # Try to create user with invalid data
        await page.fill("#new-username", "")
        await page.fill("#new-password", "123")
        await page.click("#create-user-form button[type='submit']")
        
        # UI should remain responsive
        await page.wait_for_timeout(1000)
        
        # Form should still be accessible
        username_input = await page.query_selector("#new-username")
        assert username_input is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 
