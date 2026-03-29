import { webMethod, Permissions } from 'wix-web-module';
import { fetch } from 'wix-fetch';

const API_BASE_URL = 'https://TU-API-PUBLICA.com';

export const preguntarAsistente = webMethod(
  Permissions.SiteMember,
  async (question, history = []) => {
    if (!question || !question.trim()) {
      return {
        ok: false,
        answer: 'Escribe una pregunta primero.',
        sources: [],
      };
    }

    const response = await fetch(`${API_BASE_URL}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        history,
        want_visual: true,
        render_image: false,
        max_results: 3,
      }),
    });

    if (!response.ok) {
      return {
        ok: false,
        answer: 'No pude comunicarme con la API externa.',
        visual: null,
        sources: [],
      };
    }

    return response.json();
  }
);
