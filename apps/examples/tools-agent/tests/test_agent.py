from aiapp.testing import AppTest


class Agent(AppTest):
    def test_uses_the_stock_tool(self):
        self.models.tool_call("check_stock", {"product": "grinder"}, then="Sorry, the grinder is out of stock.")
        r = self.client.post("/ask", {"question": "Do you have the grinder?"})
        self.assertEqual(r.json()["tools_used"], ["check_stock"])
        self.assertIn("out of stock", r.json()["answer"])
        self.assertIn('"in_stock": 0', str(self.models.last.messages))     # the tool's result reached the model
