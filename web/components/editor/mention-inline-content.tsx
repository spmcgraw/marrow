"use client";

import { createReactInlineContentSpec } from "@blocknote/react";

export const mentionInlineContentSpec = createReactInlineContentSpec(
  {
    type: "mention",
    propSchema: {
      userId: { default: "" },
      displayName: { default: "" },
    },
    content: "none",
  },
  {
    render: ({ inlineContent }) => {
      const props = inlineContent.props as { userId: string; displayName: string };
      return (
        <span
          className="marrow-mention"
          data-user-id={props.userId}
          contentEditable={false}
        >
          @{props.displayName}
        </span>
      );
    },
  },
);
