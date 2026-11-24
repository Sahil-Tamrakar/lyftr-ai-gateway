import React from 'react';
import { ChatMessage } from '../types/chat';
import { MessageItem } from './MessageItem';

interface Props {
  messages: ChatMessage[];
}

export const MessageList: React.FC<Props> = ({ messages }) => {
  return (
    <div className="space-y-2">
      {messages.map((msg, index) => (
        <MessageItem key={index} message={msg} />
      ))}
    </div>
  );
};
