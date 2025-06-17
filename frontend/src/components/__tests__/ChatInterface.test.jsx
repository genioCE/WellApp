import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChatInterface from '../ChatInterface';
import axios from 'axios';

jest.mock('axios');

it('sends question to backend', async () => {
  axios.post.mockResolvedValue({ data: { answer: 'hi' } });
  render(<ChatInterface />);
  fireEvent.change(screen.getByTestId('chat-well-id'), { target: { value: 'w1' } });
  fireEvent.change(screen.getByTestId('question-input'), { target: { value: 'hello' } });
  fireEvent.click(screen.getByText('Send'));
  await waitFor(() => expect(axios.post).toHaveBeenCalled());
  expect(screen.getByText(/hi/)).toBeInTheDocument();
});
