import { useState, useEffect } from 'react';
import { createNewThread, fetchThread } from "../services/api";
import { runFinishedStates } from "./constants";

export const useThread = (assistantId, run, setRun) => {
    const [threadId, setThreadId] = useState(undefined);
    const [thread, setThread] = useState(undefined);
    const [actionMessages, setActionMessages] = useState([]);
    const [messages, setMessages] = useState([]);

    // Hook responsável por criar uma nova thread se uma não existir
    useEffect(() => {
        if (threadId === undefined) {
            const localThreadId = localStorage.getItem("thread_id");
            if (localThreadId) {
                console.log(`Resuming thread ${localThreadId}`);
                setThreadId(localThreadId);
                fetchThread(localThreadId).then(setThread);
            } else {
                console.log("Creating new thread");
                createNewThread(assistantId).then((data) => {
                    if (data && data.thread_id) {
                        setRun(data);
                        setThreadId(data.thread_id);
                        localStorage.setItem("thread_id", data.thread_id);
                        console.log(`Created new thread ${data.thread_id}`);
                    } else {
                        console.error("Failed to create new thread");
                    }
                });
            }
        }
    }, [threadId, setThreadId, setThread, setRun, assistantId]);

    // Hook responsável por buscar a thread quando a execução estiver concluída
    useEffect(() => {
        if (!run || !runFinishedStates.includes(run.status)) {
            return;
        }

        if (run && run.thread_id) {
            console.log(`Retrieving thread ${run.thread_id}`);
            fetchThread(run.thread_id)
                .then((threadData) => {
                    setThread(threadData);
                })
                .catch((error) => {
                    console.error(`Failed to fetch thread ${run.thread_id}:`, error);
                });
        } else {
            console.error("run or run.thread_id is undefined");
        }
    }, [run, setThread]);

    // Hook responsável por transformar a thread em uma lista de mensagens
    useEffect(() => {
        if (!thread) {
            return;
        }
        console.log(`Transforming thread into messages`);

        let newMessages = [...thread.messages, ...actionMessages]
            .sort((a, b) => a.created_at - b.created_at)
            .filter((message) => message.hidden !== true);
        setMessages(newMessages);
    }, [thread, actionMessages, setMessages]);

    const clearThread = () => {
        localStorage.removeItem("thread_id");
        setThreadId(undefined);
        setThread(undefined);
        setRun(undefined);
        setMessages([]);
        setActionMessages([]);
    };

    return {
        threadId,
        messages,
        actionMessages,
        setActionMessages,
        clearThread
    };
};
