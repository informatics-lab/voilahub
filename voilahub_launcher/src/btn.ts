import {
    DocumentRegistry
} from '@jupyterlab/docregistry';

import {
    NotebookPanel, INotebookModel
} from '@jupyterlab/notebook';


import {
    ToolbarButton
} from '@jupyterlab/apputils';


import {
    IDisposable, DisposableDelegate
} from '@phosphor/disposable';
import '../style/index.css';


import { IDocumentManager } from '@jupyterlab/docmanager'

import { Dialog, showDialog, showErrorMessage } from '@jupyterlab/apputils';


/**
 * A notebook widget extension that adds a button to the toolbar.
 */
export class LaunchButton implements DocumentRegistry.IWidgetExtension<NotebookPanel, INotebookModel> {
    /**
     * Create a new extension object.
     */

    private documentManger: IDocumentManager;

    constructor(documentManger: IDocumentManager) {
        this.documentManger = documentManger
    }

    createNew(panel: NotebookPanel, context: DocumentRegistry.IContext<INotebookModel>): IDisposable {

        let callback = () => {

            console.log(panel.context.path)
            fetch("/services/voilahub/system").then(res => res.json()).then(
                (config) => {
                    let share = config.public_share
                    while (share[share.length - 1] === '/') {
                        share += share.substr(0, share.length - 1)
                    }
                    let copyFrom = panel.context.path

                    console.log(`copy from ${copyFrom} to ${share}`)
                    this.documentManger.copy(copyFrom, share).then((res) => {
                        let url = `${window.location.origin}/services/voilahub/launch/default/${share}/${res.name}`
                        console.log('success!', url)
                        showDialog({
                            title: 'Rename File',
                            body: `Please share this url: ${url}`,
                            buttons: [Dialog.okButton({ label: 'Ok' })]
                        })
                    }, () => {
                        showErrorMessage(
                            'Rename Error',
                            Error("Failed to publish")
                        )
                    }
                    )
                }
            )
        };

        let openChatBtn = new ToolbarButton({
            className: 'voilahub_publish',
            onClick: callback,
            tooltip: 'Publish on Voila Hub',

            iconClassName: 'fa fa-share-alt-square'
        });


        panel.toolbar.insertItem(0, 'chat', openChatBtn);
        return new DisposableDelegate(() => {
            openChatBtn.dispose();
        });
    }
}