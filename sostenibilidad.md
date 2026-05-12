# Por qué Gemini API es más sostenible que Ollama local

## Infraestructura especializada vs hardware de consumo

Los modelos de Ollama corren en CPU/GPU de consumo. La eficiencia energética de un portátil o PC haciendo inferencia local es mala comparada con infraestructura especializada:

- **Google data centers**: PUE (Power Usage Effectiveness) de ~1.10, prácticamente el mejor del sector. Por cada watio de cómputo, solo gastan 0.10 W extra en refrigeración.
- **Hardware local**: PUE implícito mucho peor, calefacción de la habitación incluida.
- **TPUs de Google**: diseñados específicamente para redes neuronales, órdenes de magnitud más eficientes por inferencia que una GPU de consumo.

## Energía renovable

Google tiene uno de los compromisos de energía renovable más sólidos del sector: objetivo de **24/7 carbon-free energy para 2030**. Cuando la app llama a Gemini, la inferencia se ejecuta en infraestructura con un mix energético muy limpio.

Un PC de escritorio o portátil se alimenta de lo que salga de la red eléctrica local, sin ninguna garantía de origen renovable.

## Eficiencia por escala

Google ejecuta millones de inferencias sobre el mismo hardware simultáneamente. La amortización energética por consulta es mínima. Con Ollama, el modelo entero está cargado en memoria consumiendo recursos aunque no se esté usando.

## Conclusión

> Usar Gemini API es más sostenible porque delegamos la inferencia en infraestructura especializada con energía renovable, en vez de quemar ciclos de CPU/GPU en hardware de consumo.
