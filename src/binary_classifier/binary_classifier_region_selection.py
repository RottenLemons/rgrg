import torch.nn as nn


class BinaryClassifierRegionSelection(nn.Module):
    def __init__(self):
        super().__init__()

        self.classifier = nn.Sequential(
            nn.Linear(in_features=1024, out_features=512),
            nn.ReLU(),
            nn.Linear(in_features=512, out_features=128),
            nn.ReLU(),
            nn.Linear(in_features=128, out_features=1)
        )

        self.loss_fn = nn.BCEWithLogitsLoss()

    def forward(
        self,
        top_region_features,  # tensor of shape [batch_size x 36 x 1024]
        class_detected,  # boolean tensor of shape [batch_size x 36], indicates if the object detector has detected the region/class or not
        return_loss,  # boolean value that is True if we need the loss (necessary for training and evaluation)
        region_has_sentence=None  # boolean tensor of shape [batch_size x 36], indicates if a region has a sentence (True) or not (False) as the ground truth
    ):
        # logits of shape [batch_size x 36]
        logits = self.classifier(top_region_features).squeeze(dim=-1)

        # the loss is needed for training and evaluation
        if return_loss:
            # only compute loss for logits that correspond to a class that was detected
            detected_logits = logits[class_detected]
            detected_region_has_sentence = region_has_sentence[class_detected]
            loss = self.loss_fn(detected_logits, detected_region_has_sentence)

        if self.training:
            return loss
        else:
            # compute selected_regions for evaluation and inference
            # selected_regions are the predictions by the classifier, has shape [batch_size x 36] and is True for regions that should get a sentence
            # selected_regions are needed to filter the top_region_features to those that the classifier selected for sentence generation,
            # to evaluate the classifier during eval mode (comparing selected_regions to ground-truth region_has_sentence to compute recall, precision etc.)
            # and to generally know which regions were selected for generation (which is needed for mapping each selected_region_feature to its corresponding class)
            #
            # use a threshold of 0 in logit-space (i.e. 0.5 in probability-space)
            # if a logit > 0, then it means that class/region has boolean value True and a sentence should be generated for it
            selected_regions = logits > 0

            # set to False all regions that were not detected by object detector
            # (since no detection -> no sentence generation possible)
            selected_regions[~class_detected] = False

            # selected_region_features are inputted into the decoder during evaluation and inference to generate the sentences
            # selected_region_features is of shape [num_regions_selected_in_batch, 1024]
            selected_region_features = top_region_features[selected_regions]

            # if in eval mode
            if return_loss:
                return loss, selected_regions, selected_region_features
            else:
                # if in inference mode
                return selected_regions, selected_region_features