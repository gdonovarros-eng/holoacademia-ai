import { preguntarAsistente } from 'backend/aiApi.web';

const chatHistory = [];

function formatearVisual(visual) {
    if (!visual || visual.type === 'none') {
        return '';
    }

    if (visual.format === 'image_prompt' && visual.image_prompt) {
        return `${visual.title}\nIdea de imagen:\n${visual.image_prompt}`;
    }

    if (visual.format === 'mermaid' && visual.content) {
        return `${visual.title}\nDiagrama sugerido:\n${visual.content}`;
    }

    if (visual.content) {
        return `${visual.title}\n${visual.content}`;
    }

    return '';
}

$w.onReady(function () {
    $w('#text1094').text = 'Escribe una pregunta para comenzar.';

    $w('#button36').onClick(async function () {
        const pregunta = $w('#input1').value;

        if (!pregunta) {
            $w('#text1094').text = 'Escribe una pregunta primero.';
            return;
        }

        $w('#text1094').text = 'Pensando...';

        try {
            const resultado = await preguntarAsistente(pregunta, chatHistory);

            if (!resultado.ok) {
                $w('#text1094').text = resultado.answer || 'No encontré una respuesta.';
                return;
            }

            let mensaje = resultado.answer || '';
            const visual = formatearVisual(resultado.visual);
            if (visual) {
                mensaje += `\n\n${visual}`;
            }

            chatHistory.push({ role: 'user', content: pregunta });
            chatHistory.push({ role: 'assistant', content: resultado.answer || '' });
            if (chatHistory.length > 8) {
                chatHistory.splice(0, chatHistory.length - 8);
            }

            $w('#text1094').text = mensaje;
        } catch (error) {
            console.error('Error consultando la API externa:', error);
            $w('#text1094').text = 'Ocurrió un error al consultar el asistente.';
        }
    });
});
